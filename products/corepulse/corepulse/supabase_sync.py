"""
CorePulse Supabase Offline-First Sync Module Adapter
Exports core classes and singleton from products/corepulse/sync_supabase.py
"""

from sync_supabase import (
    HybridLogicalClock,
    FieldLevelCRDTResolver,
    SupabaseConfig,
    SupabaseRestClient,
    SupabaseOfflineSync,
    supabase_sync,
)

__all__ = [
    "HybridLogicalClock",
    "FieldLevelCRDTResolver",
    "SupabaseConfig",
    "SupabaseRestClient",
    "SupabaseOfflineSync",
    "supabase_sync",
]
