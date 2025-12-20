-- Supabase Database Schema for Backtest Results Storage
-- This allows UI to query only what it needs, avoiding huge data transfers

-- ============================================================================
-- Table 1: Backtest Jobs (metadata about each backtest run)
-- ============================================================================
CREATE TABLE IF NOT EXISTS backtest_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, running, completed, failed
    
    -- Results summary
    total_days INTEGER DEFAULT 0,
    total_transactions INTEGER DEFAULT 0,
    total_pnl DECIMAL(12, 2) DEFAULT 0,
    win_rate DECIMAL(5, 2) DEFAULT 0,
    total_winning_trades INTEGER DEFAULT 0,
    total_losing_trades INTEGER DEFAULT 0,
    largest_win DECIMAL(12, 2) DEFAULT 0,
    largest_loss DECIMAL(12, 2) DEFAULT 0,
    
    -- Job metadata
    include_diagnostics BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    
    -- User info (if multi-user)
    user_id UUID,
    
    -- Indexes for fast queries
    CONSTRAINT backtest_jobs_status_check CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_backtest_jobs_strategy ON backtest_jobs(strategy_id);
CREATE INDEX IF NOT EXISTS idx_backtest_jobs_status ON backtest_jobs(status);
CREATE INDEX IF NOT EXISTS idx_backtest_jobs_created ON backtest_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backtest_jobs_user ON backtest_jobs(user_id);

-- ============================================================================
-- Table 2: Daily Summaries (one row per trading day)
-- ============================================================================
CREATE TABLE IF NOT EXISTS backtest_daily_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES backtest_jobs(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    -- Daily metrics
    total_positions INTEGER DEFAULT 0,
    closed_positions INTEGER DEFAULT 0,
    open_positions INTEGER DEFAULT 0,
    total_pnl DECIMAL(12, 2) DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    breakeven_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5, 2) DEFAULT 0,
    largest_win DECIMAL(12, 2) DEFAULT 0,
    largest_loss DECIMAL(12, 2) DEFAULT 0,
    avg_win DECIMAL(12, 2) DEFAULT 0,
    avg_loss DECIMAL(12, 2) DEFAULT 0,
    avg_duration_minutes DECIMAL(8, 2) DEFAULT 0,
    re_entries INTEGER DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(job_id, date)
);

CREATE INDEX IF NOT EXISTS idx_daily_summaries_job ON backtest_daily_summaries(job_id);
CREATE INDEX IF NOT EXISTS idx_daily_summaries_date ON backtest_daily_summaries(job_id, date);

-- ============================================================================
-- Table 3: Transactions (one row per transaction with summary data)
-- ============================================================================
CREATE TABLE IF NOT EXISTS backtest_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES backtest_jobs(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    -- Transaction identifiers
    position_id VARCHAR(100) NOT NULL,
    position_number INTEGER NOT NULL,
    transaction_number INTEGER NOT NULL,
    re_entry_num INTEGER DEFAULT 0,
    
    -- Entry/Exit info
    entry_node_id VARCHAR(100),
    exit_node_id VARCHAR(100),
    entry_time TIMESTAMP WITH TIME ZONE,
    entry_timestamp VARCHAR(20),
    exit_time TIMESTAMP WITH TIME ZONE,
    exit_timestamp VARCHAR(20),
    
    -- Contract details
    symbol VARCHAR(200),
    instrument VARCHAR(50),
    strike VARCHAR(20),
    option_type VARCHAR(10), -- CE, PE
    expiry DATE,
    exchange VARCHAR(20),
    
    -- Trade details
    entry_price DECIMAL(12, 2),
    exit_price DECIMAL(12, 2),
    quantity INTEGER,
    lot_size INTEGER,
    
    -- P&L
    pnl DECIMAL(12, 2),
    pnl_percentage DECIMAL(8, 2),
    
    -- Duration
    duration_seconds DECIMAL(10, 2),
    duration_minutes DECIMAL(10, 2),
    
    -- Status
    status VARCHAR(20), -- OPEN, CLOSED
    exit_reason VARCHAR(100),
    
    -- Market context
    nifty_spot_at_entry DECIMAL(12, 2),
    nifty_spot_at_exit DECIMAL(12, 2),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_job ON backtest_transactions(job_id);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON backtest_transactions(job_id, date);
CREATE INDEX IF NOT EXISTS idx_transactions_position ON backtest_transactions(position_id);
CREATE INDEX IF NOT EXISTS idx_transactions_pnl ON backtest_transactions(pnl);
CREATE INDEX IF NOT EXISTS idx_transactions_entry_time ON backtest_transactions(entry_time);

-- ============================================================================
-- Table 4: Transaction Diagnostics (separate table, loaded on-demand)
-- ============================================================================
CREATE TABLE IF NOT EXISTS backtest_transaction_diagnostics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES backtest_transactions(id) ON DELETE CASCADE,
    
    -- Diagnostic text (formatted for display)
    diagnostic_text TEXT,
    
    -- Entry diagnostic data (JSONB for flexible querying)
    entry_conditions_evaluated JSONB, -- Array of condition evaluations
    entry_candle_data JSONB, -- Candle OHLC data
    entry_condition_preview TEXT,
    entry_node_variables JSONB,
    
    -- Exit diagnostic data
    exit_conditions_evaluated JSONB,
    exit_candle_data JSONB,
    exit_condition_preview TEXT,
    exit_node_variables JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(transaction_id)
);

CREATE INDEX IF NOT EXISTS idx_diagnostics_transaction ON backtest_transaction_diagnostics(transaction_id);

-- ============================================================================
-- Row Level Security (RLS) - Enable if multi-user
-- ============================================================================
-- ALTER TABLE backtest_jobs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE backtest_daily_summaries ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE backtest_transactions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE backtest_transaction_diagnostics ENABLE ROW LEVEL SECURITY;

-- RLS Policies (example for multi-user)
-- CREATE POLICY "Users can view their own backtests" ON backtest_jobs
--     FOR SELECT USING (auth.uid() = user_id);

-- ============================================================================
-- Helper Views for Common Queries
-- ============================================================================

-- View: Recent backtest jobs with summary
CREATE OR REPLACE VIEW backtest_jobs_summary AS
SELECT 
    j.id,
    j.strategy_id,
    j.start_date,
    j.end_date,
    j.status,
    j.total_transactions,
    j.total_pnl,
    j.win_rate,
    j.created_at,
    j.completed_at,
    EXTRACT(EPOCH FROM (j.completed_at - j.started_at)) as duration_seconds
FROM backtest_jobs j
ORDER BY j.created_at DESC;

-- View: Transaction summary with key metrics
CREATE OR REPLACE VIEW transactions_summary AS
SELECT 
    t.id,
    t.job_id,
    t.date,
    t.position_number,
    t.transaction_number,
    t.entry_timestamp,
    t.exit_timestamp,
    t.strike,
    t.option_type,
    t.entry_price,
    t.exit_price,
    t.pnl,
    t.pnl_percentage,
    t.duration_minutes,
    t.status,
    CASE WHEN t.pnl > 0 THEN 'win'
         WHEN t.pnl < 0 THEN 'loss'
         ELSE 'breakeven'
    END as trade_outcome
FROM backtest_transactions t;

-- ============================================================================
-- Performance Notes:
-- ============================================================================
-- 1. Transactions table: ~25,000 rows for 1 year = ~5 MB (no diagnostics)
-- 2. Diagnostics table: Separate, loaded only when user clicks transaction
-- 3. Daily summaries: 250 rows for 1 year = minimal
-- 4. UI queries: Fast, indexed, paginated
-- 5. Total storage: ~10-20 MB per year (very manageable!)
