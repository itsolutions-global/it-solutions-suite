-- ==============================================================================
-- IT Solutions Global Corporation — CorePulse Enterprise Cloud Federation
-- Migration 001: Supabase PostgreSQL Schema, Realtime CDC & Multi-Tenant RLS
-- Target: Supabase Managed PostgreSQL 16+
-- ==============================================================================

-- Create dedicated corepulse schema
CREATE SCHEMA IF NOT EXISTS corepulse;

-- 1. Tasks Table (Relational mirror for CorePulse tasks & habits)
CREATE TABLE IF NOT EXISTS corepulse.tasks (
    id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    type TEXT DEFAULT 'task',
    category TEXT DEFAULT 'General',
    priority TEXT DEFAULT 'medium',
    completed BOOLEAN DEFAULT FALSE,
    due_date TEXT DEFAULT 'Today',
    estimated_minutes INTEGER DEFAULT 30,
    streak_days INTEGER DEFAULT 0,
    tags JSONB DEFAULT '[]'::jsonb,
    hlc TEXT NOT NULL,
    lamport_clock BIGINT NOT NULL DEFAULT 1,
    client_id TEXT NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE,
    encrypted_payload TEXT,
    auth_tag TEXT,
    iv TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, tenant_id)
);

-- Indexing for high-throughput tenant filtering and delta pull queries
CREATE INDEX IF NOT EXISTS idx_tasks_tenant_updated 
ON corepulse.tasks (tenant_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_tasks_tenant_hlc 
ON corepulse.tasks (tenant_id, hlc DESC);

-- 2. Habits Table
CREATE TABLE IF NOT EXISTS corepulse.habits (
    id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT DEFAULT 'Ritual',
    streak_count INTEGER DEFAULT 0,
    target_frequency TEXT DEFAULT 'daily',
    last_completed_at TIMESTAMPTZ,
    hlc TEXT NOT NULL,
    lamport_clock BIGINT NOT NULL DEFAULT 1,
    client_id TEXT NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_habits_tenant_updated 
ON corepulse.habits (tenant_id, updated_at DESC);

-- 3. Audit & Conflict Ledger Table (Immutable record of CRDT resolutions)
CREATE TABLE IF NOT EXISTS corepulse.sync_conflict_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    field_name TEXT DEFAULT 'all',
    winning_client_id TEXT NOT NULL,
    winning_hlc TEXT NOT NULL,
    winning_lamport BIGINT NOT NULL,
    losing_client_id TEXT NOT NULL,
    losing_hlc TEXT NOT NULL,
    losing_lamport BIGINT NOT NULL,
    resolution_strategy TEXT DEFAULT 'FIELD_LWW_CRDT',
    resolved_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conflicts_tenant 
ON corepulse.sync_conflict_ledger (tenant_id, resolved_at DESC);

-- ==============================================================================
-- Row-Level Security (RLS) Policies
-- Strict Multi-Tenant Isolation: tenant_id = (auth.jwt() ->> 'tenant_id')
-- ==============================================================================

-- Enable RLS
ALTER TABLE corepulse.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE corepulse.habits ENABLE ROW LEVEL SECURITY;
ALTER TABLE corepulse.sync_conflict_ledger ENABLE ROW LEVEL SECURITY;

-- Tasks Policies
CREATE POLICY tasks_tenant_isolation_select ON corepulse.tasks
    FOR SELECT
    USING (tenant_id = (auth.jwt() ->> 'tenant_id'));

CREATE POLICY tasks_tenant_isolation_insert ON corepulse.tasks
    FOR INSERT
    WITH CHECK (
        tenant_id = (auth.jwt() ->> 'tenant_id') AND
        user_id = (auth.jwt() ->> 'sub')
    );

CREATE POLICY tasks_tenant_isolation_update ON corepulse.tasks
    FOR UPDATE
    USING (tenant_id = (auth.jwt() ->> 'tenant_id'))
    WITH CHECK (tenant_id = (auth.jwt() ->> 'tenant_id'));

CREATE POLICY tasks_tenant_isolation_delete ON corepulse.tasks
    FOR DELETE
    USING (
        tenant_id = (auth.jwt() ->> 'tenant_id') AND
        (
            (auth.jwt() ->> 'user_role') IN ('owner', 'admin') OR
            user_id = (auth.jwt() ->> 'sub')
        )
    );

-- Habits Policies
CREATE POLICY habits_tenant_isolation_select ON corepulse.habits
    FOR SELECT 
    USING (tenant_id = (auth.jwt() ->> 'tenant_id'));

CREATE POLICY habits_tenant_isolation_insert ON corepulse.habits
    FOR INSERT 
    WITH CHECK (
        tenant_id = (auth.jwt() ->> 'tenant_id') AND
        user_id = (auth.jwt() ->> 'sub')
    );

CREATE POLICY habits_tenant_isolation_update ON corepulse.habits
    FOR UPDATE 
    USING (tenant_id = (auth.jwt() ->> 'tenant_id'))
    WITH CHECK (tenant_id = (auth.jwt() ->> 'tenant_id'));

CREATE POLICY habits_tenant_isolation_delete ON corepulse.habits
    FOR DELETE 
    USING (
        tenant_id = (auth.jwt() ->> 'tenant_id') AND
        (auth.jwt() ->> 'user_role') IN ('owner', 'admin')
    );

-- Conflict Ledger Policies
CREATE POLICY conflict_ledger_select ON corepulse.sync_conflict_ledger
    FOR SELECT 
    USING (tenant_id = (auth.jwt() ->> 'tenant_id'));

CREATE POLICY conflict_ledger_insert ON corepulse.sync_conflict_ledger
    FOR INSERT 
    WITH CHECK (tenant_id = (auth.jwt() ->> 'tenant_id'));

-- ==============================================================================
-- Realtime CDC Publications
-- ==============================================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE corepulse.tasks;
        ALTER PUBLICATION supabase_realtime ADD TABLE corepulse.habits;
    END IF;
END $$;
