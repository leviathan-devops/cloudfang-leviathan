//! Token budget tracking and proactive rate limit detection.
//!
//! Tracks tokens consumed per agent per hour and proactively detects when
//! an agent is approaching or has exceeded its token budget. This enables
//! graceful model fallback instead of crashes.
//!
//! Detection thresholds:
//! - 90%: Logs a WARNING
//! - 95%: Switches to the first fallback_model in the agent's manifest
//! - 100%: Blocks the request with a clear error message

use chrono::Utc;
use openfang_memory::usage::{UsageStore, UsageSummary};
use openfang_types::agent::{AgentId, FallbackModel, ResourceQuota};
use openfang_types::error::{OpenFangError, OpenFangResult};
use std::sync::Arc;
use tracing::{warn, info, debug};

/// Tracks token budget usage per agent and detects rate limit conditions.
pub struct TokenBudgetTracker {
    /// Persistent usage store for querying historical token usage.
    usage_store: Arc<UsageStore>,
}

impl TokenBudgetTracker {
    /// Create a new token budget tracker.
    pub fn new(usage_store: Arc<UsageStore>) -> Self {
        Self { usage_store }
    }

    /// Check if an agent's token budget is exhausted or approaching limits.
    ///
    /// Returns a `BudgetCheckResult` indicating the agent's budget status.
    pub fn check_budget(&self, agent_id: AgentId, quota: &ResourceQuota) -> OpenFangResult<BudgetCheckResult> {
        if quota.max_llm_tokens_per_hour == 0 {
            // No budget limit configured
            return Ok(BudgetCheckResult {
                status: BudgetStatus::Unlimited,
                tokens_used: 0,
                max_tokens: 0,
            });
        }

        // Query hourly token usage for this agent
        let summary = self.usage_store.query_hourly_tokens(agent_id)?;
        let tokens_used = summary.total_input_tokens + summary.total_output_tokens;
        let max_tokens = quota.max_llm_tokens_per_hour;

        // Calculate usage percentage
        let usage_percent = if max_tokens > 0 {
            (tokens_used as f64 / max_tokens as f64) * 100.0
        } else {
            0.0
        };

        // Determine budget status based on thresholds
        let status = if tokens_used >= max_tokens {
            // At or over 100%: budget exhausted
            warn!(
                agent_id = %agent_id,
                tokens_used = tokens_used,
                max_tokens = max_tokens,
                usage_percent = format!("{:.1}%", usage_percent),
                "Agent has exhausted hourly token budget"
            );
            BudgetStatus::Exhausted { tokens_used, max_tokens }
        } else if usage_percent >= 95.0 {
            // At 95%+: critical
            warn!(
                agent_id = %agent_id,
                tokens_used = tokens_used,
                max_tokens = max_tokens,
                usage_percent = format!("{:.1}%", usage_percent),
                "Agent approaching token limit (95%+), will switch to fallback model"
            );
            BudgetStatus::Critical { tokens_used, max_tokens, percent: usage_percent }
        } else if usage_percent >= 90.0 {
            // At 90%+: warning
            warn!(
                agent_id = %agent_id,
                tokens_used = tokens_used,
                max_tokens = max_tokens,
                usage_percent = format!("{:.1}%", usage_percent),
                "Agent approaching token limit (90%+)"
            );
            BudgetStatus::Warning { tokens_used, max_tokens, percent: usage_percent }
        } else {
            // Under 90%: healthy
            debug!(
                agent_id = %agent_id,
                tokens_used = tokens_used,
                max_tokens = max_tokens,
                usage_percent = format!("{:.1}%", usage_percent),
                "Token budget healthy"
            );
            BudgetStatus::Healthy { tokens_used, max_tokens }
        };

        Ok(BudgetCheckResult {
            status,
            tokens_used,
            max_tokens,
        })
    }

    /// Select a fallback model when the primary model has hit rate limits.
    ///
    /// Returns the first available fallback model, or an error if none are configured.
    pub fn select_fallback_model(
        fallback_models: &[FallbackModel],
    ) -> OpenFangResult<FallbackModel> {
        fallback_models.first()
            .cloned()
            .ok_or_else(|| OpenFangError::QuotaExceeded(
                "Token budget exhausted: no fallback models configured".into()
            ))
    }
}

/// Result of a token budget check.
#[derive(Debug, Clone)]
pub struct BudgetCheckResult {
    /// The budget status (Healthy, Warning, Critical, or Exhausted).
    pub status: BudgetStatus,
    /// Tokens used so far in the current hour.
    pub tokens_used: u64,
    /// Maximum tokens allowed per hour.
    pub max_tokens: u64,
}

/// Budget status enumeration.
#[derive(Debug, Clone)]
pub enum BudgetStatus {
    /// No budget limit is configured.
    Unlimited,
    /// Tokens consumed is under 90% of the limit.
    Healthy {
        /// Tokens used in the current hour.
        tokens_used: u64,
        /// Maximum tokens allowed per hour.
        max_tokens: u64,
    },
    /// Tokens consumed is 90%+ but under 95% of the limit.
    Warning {
        /// Tokens used in the current hour.
        tokens_used: u64,
        /// Maximum tokens allowed per hour.
        max_tokens: u64,
        /// Usage percentage (90.0 to 94.9).
        percent: f64,
    },
    /// Tokens consumed is 95%+ but under 100% of the limit.
    /// A fallback model should be selected.
    Critical {
        /// Tokens used in the current hour.
        tokens_used: u64,
        /// Maximum tokens allowed per hour.
        max_tokens: u64,
        /// Usage percentage (95.0 to 99.9).
        percent: f64,
    },
    /// Tokens consumed is at or above 100% of the limit.
    /// The request should be blocked.
    Exhausted {
        /// Tokens used in the current hour.
        tokens_used: u64,
        /// Maximum tokens allowed per hour.
        max_tokens: u64,
    },
}

impl BudgetStatus {
    /// Returns true if the budget is exhausted.
    pub fn is_exhausted(&self) -> bool {
        matches!(self, BudgetStatus::Exhausted { .. })
    }

    /// Returns true if a fallback should be attempted.
    pub fn should_fallback(&self) -> bool {
        matches!(self, BudgetStatus::Critical { .. })
    }

    /// Returns true if only a warning should be logged.
    pub fn is_warning(&self) -> bool {
        matches!(self, BudgetStatus::Warning { .. })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_budget_status_exhausted() {
        let status = BudgetStatus::Exhausted {
            tokens_used: 1_000_000,
            max_tokens: 1_000_000,
        };
        assert!(status.is_exhausted());
        assert!(!status.should_fallback());
    }

    #[test]
    fn test_budget_status_critical() {
        let status = BudgetStatus::Critical {
            tokens_used: 950_000,
            max_tokens: 1_000_000,
            percent: 95.0,
        };
        assert!(!status.is_exhausted());
        assert!(status.should_fallback());
    }

    #[test]
    fn test_budget_status_warning() {
        let status = BudgetStatus::Warning {
            tokens_used: 900_000,
            max_tokens: 1_000_000,
            percent: 90.0,
        };
        assert!(!status.is_exhausted());
        assert!(!status.should_fallback());
        assert!(status.is_warning());
    }

    #[test]
    fn test_budget_status_healthy() {
        let status = BudgetStatus::Healthy {
            tokens_used: 500_000,
            max_tokens: 1_000_000,
        };
        assert!(!status.is_exhausted());
        assert!(!status.should_fallback());
        assert!(!status.is_warning());
    }

    #[test]
    fn test_select_fallback_model_success() {
        let fallbacks = vec![
            FallbackModel {
                provider: "groq".to_string(),
                model: "llama-3.3-70b".to_string(),
                api_key_env: None,
                base_url: None,
            },
            FallbackModel {
                provider: "together".to_string(),
                model: "mistral-7b".to_string(),
                api_key_env: None,
                base_url: None,
            },
        ];
        let selected = TokenBudgetTracker::select_fallback_model(&fallbacks).unwrap();
        assert_eq!(selected.provider, "groq");
        assert_eq!(selected.model, "llama-3.3-70b");
    }

    #[test]
    fn test_select_fallback_model_empty() {
        let fallbacks: Vec<FallbackModel> = vec![];
        let result = TokenBudgetTracker::select_fallback_model(&fallbacks);
        assert!(result.is_err());
    }
}
