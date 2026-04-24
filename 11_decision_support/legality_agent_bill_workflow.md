# Legality checker agent: end-to-end bill / clause workflow

User upload → user-scoped context → clause decomposition and sub-agents → RAG and external retrieval → per-clause legal assessment → aggregated response → user-scoped storage (no cross-user draft leakage).

```mermaid
flowchart TB
  subgraph userEntry [1_User_and_draft]
    U[User]
    Draft[Upload_bill_draft_PDF_or_DOCX]
    U --> Draft
  end

  subgraph sessionCtx [2_User_context_no_crossuser_leak]
    UID[Resolve_userId]
    CH[Load_prior_chats_and_drafts_for_this_user_only]
    UID --> CH
  end

  Draft --> UID

  subgraph orchestrator [3_Orchestrator_agent]
    Split[Parse_and_split_bill_into_clauses]
    Spawn[Assign_each_clause_to_subagent]
    Split --> Spawn
  end

  CH --> Split

  subgraph parallelClauses [4_Parallel_clause_subagents]
    A1[Clause_subagent_1]
    A2[Clause_subagent_2]
    AK[Clause_subagent_k]
  end

  Spawn --> A1
  Spawn --> A2
  Spawn --> AK

  subgraph retrieve [5_Retrieval_per_clause]
    RAG[RAG_over_statutes_case_law_rulings_corpus]
    WEB[Targeted_web_or_licensed_DB_search]
    Filt[Filter_deduplicate_and_quote_level_citations]
  end

  A1 --> RAG
  A1 --> WEB
  A2 --> RAG
  A2 --> WEB
  AK --> RAG
  AK --> WEB
  RAG --> Filt
  WEB --> Filt

  subgraph judgment [6_Clause_level_assessment]
    Rate[Classify_Legal_Illegal_Unknown]
    Conf[Confidence_1_to_5]
    Sup[Docs_supporting_position_with_section_pointer]
    Opp[Docs_opposing_position_with_section_pointer]
    Filt --> Rate
    Rate --> Conf
    Rate --> Sup
    Rate --> Opp
  end

  subgraph aggregate [7_Response_to_user]
    Merge[Merge_clause_reports_into_single_bill_level_answer]
    Conf --> Merge
    Sup --> Merge
    Opp --> Merge
  end

  subgraph persist [8_User_scoped_storage]
    Store[Write_chat_clause_results_and_pointers_tied_to_userId]
    RBAC[Enforce_tenant_isolation_RLS_or_equivalent]
    Store --> RBAC
  end

  Merge --> Store
  Merge --> R[Return_structured_legal_memo_to_user]
```

**Retrieval note:** The `Targeted_web_or_licensed_DB_search` node is generic on purpose. In production, public sources (e.g., statutes, Congress.gov) may be open, while paywalled systems (Westlaw, Lexis, PACER) should be accessed through enterprise APIs or allowed connectors, not ad hoc scraping, according to your organization’s policy.
