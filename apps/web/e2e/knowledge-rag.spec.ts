import { test, expect, Page } from "@playwright/test";

interface MockCallParams {
  callId: string;
  callerNumber: string;
}

async function setupMockCallWithKnowledge(
  page: Page,
  primaryCall: MockCallParams = {
    callId: "call-rag-test-01",
    callerNumber: "+91******7890",
  },
  secondaryCall?: MockCallParams
) {
  // Prevent background WebSocket from racing or disconnecting
  await page.route("**/ws/operator", (route) => route.abort());

  const activeCalls = [
    {
      call_id: primaryCall.callId,
      caller_masked_number: primaryCall.callerNumber,
      state: "STREAMING",
      conversation_state: "LISTENING",
      current_language: "ta-IN",
      duration_seconds: 75,
      provider: "exotel",
      is_active: true,
      safety_state: "NONE",
      safety_signals_count: 0,
      svi_score: 38,
      svi_band: "LOW",
      ownership_state: "AI_ASSISTED",
      notes_count: 0,
    },
  ];

  if (secondaryCall) {
    activeCalls.push({
      call_id: secondaryCall.callId,
      caller_masked_number: secondaryCall.callerNumber,
      state: "STREAMING",
      conversation_state: "LISTENING",
      current_language: "hi-IN",
      duration_seconds: 20,
      provider: "exotel",
      is_active: true,
      safety_state: "NONE",
      safety_signals_count: 0,
      svi_score: 40,
      svi_band: "MODERATE",
      ownership_state: "AI_ASSISTED",
      notes_count: 0,
    });
  }

  // Active calls list
  await page.route("**/v1/calls", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        active_calls: activeCalls,
        recent_calls: [],
      }),
    });
  });

  // Call detail for primary
  await page.route(`**/v1/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: primaryCall.callId,
        caller_masked_number: primaryCall.callerNumber,
        state: "STREAMING",
        conversation_state: "LISTENING",
        current_language: "ta-IN",
        safety_state: "NONE",
        duration_seconds: 75,
        provider: "exotel",
        is_active: true,
      }),
    });
  });

  await page.route(`**/v1/calls/${primaryCall.callId}/transcript`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: primaryCall.callId,
        utterances: [
          {
            utterance_id: "utt-rag-001",
            speaker: "caller",
            text: "நான் தமிழ்நாட்டில் கல்வி உதவித்தொகை தகுதி விதிகளை அறிய விரும்புகிறேன்.",
            language: "ta-IN",
            safety_flag: false,
            created_at: new Date().toISOString(),
          },
        ],
      }),
    });
  });

  await page.route(`**/v1/calls/${primaryCall.callId}/events`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: primaryCall.callId,
        events: [
          {
            event_id: "ev-k-01",
            call_id: primaryCall.callId,
            event_type: "KNOWLEDGE_SEARCH_STARTED",
            timestamp: new Date().toISOString(),
            payload: {
              query_text: "scholarship eligibility criteria",
              jurisdiction: "TAMIL_NADU",
            },
          },
          {
            event_id: "ev-k-02",
            call_id: primaryCall.callId,
            event_type: "KNOWLEDGE_SEARCH_COMPLETED",
            timestamp: new Date().toISOString(),
            payload: {
              query_text: "scholarship eligibility criteria",
              status: "GROUNDED",
              total_found: 2,
              citations: [
                {
                  citation_id: "cit-test-scholarship-01",
                  source_id: "doc-tn-scholarship",
                  title: "TN Higher Education Scholarship Guidelines",
                },
              ],
            },
          },
        ],
      }),
    });
  });

  // Safety, SVI, Acoustic, Adaptive, Orchestration endpoints
  await page.route(`**/v1/safety/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ call_id: primaryCall.callId, safety_state: "NONE", safety_signals: [] }),
    });
  });

  await page.route(`**/v1/svi/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ call_id: primaryCall.callId, score: 38, band: "LOW", trend: "STABLE" }),
    });
  });

  await page.route(`**/v1/acoustic/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ call_id: primaryCall.callId, quality: "GOOD", confidence: 0.95, operational_signals: [] }),
    });
  });

  await page.route(`**/v1/adaptive/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ call_id: primaryCall.callId, action: "SUPPORTIVE_INQUIRY", priority: "P3" }),
    });
  });

  await page.route(`**/v1/adaptive/calls/${primaryCall.callId}/history`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ strategies: [] }),
    });
  });

  await page.route(`**/v1/orchestration/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        request_id: "req-k-01",
        call_id: primaryCall.callId,
        turn_id: "utt-rag-001",
        state: "COMPLETED",
        selected_agents: ["knowledge_retrieval_agent", "operator_briefing_agent"],
        completed_agents: ["knowledge_retrieval_agent", "operator_briefing_agent"],
        failed_agents: [],
        timed_out_agents: [],
        cancelled_agents: [],
        total_latency_ms: 85,
        briefing: {
          safety_summary: "No safety cues detected.",
          svi_summary: "SVI 38 (LOW tier).",
          acoustic_summary: "Normal pitch and speech rate.",
          adaptive_recommendation: "Provide verified policy scholarship guidance.",
          key_facts: ["Caller inquiring about TN scholarship"],
          evidence_refs: ["cit:cit-test-scholarship-01"],
          confidence: 0.96,
        },
      }),
    });
  });

  // Operator snapshot & notes
  await page.route(`**/v1/operator/calls/${primaryCall.callId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: primaryCall.callId,
        ownership_state: "AI_ASSISTED",
        handoff_status: "AVAILABLE",
        adaptive_paused: false,
      }),
    });
  });

  let notesStorage: any[] = [];
  await page.route(`**/v1/operator/calls/${primaryCall.callId}/notes`, async (route) => {
    if (route.request().method() === "POST") {
      const payload = JSON.parse(route.request().postData() || "{}");
      const newNote = {
        note_id: `note-${Date.now()}`,
        call_id: primaryCall.callId,
        operator_id: payload.operator_id || "operator_1",
        category: payload.category || "GENERAL",
        text: payload.text || "",
        citation_ref: payload.citation_ref,
        timestamp: new Date().toISOString(),
        is_structured: true,
      };
      notesStorage.unshift(newNote);
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify(newNote),
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ notes: notesStorage }),
      });
    }
  });

  // Secondary call setup if present
  if (secondaryCall) {
    await page.route(`**/v1/calls/${secondaryCall.callId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          call_id: secondaryCall.callId,
          caller_masked_number: secondaryCall.callerNumber,
          state: "STREAMING",
          conversation_state: "LISTENING",
          current_language: "hi-IN",
          safety_state: "NONE",
          duration_seconds: 20,
          provider: "exotel",
          is_active: true,
        }),
      });
    });

    await page.route(`**/v1/calls/${secondaryCall.callId}/transcript`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ call_id: secondaryCall.callId, utterances: [] }),
      });
    });

    await page.route(`**/v1/calls/${secondaryCall.callId}/events`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ call_id: secondaryCall.callId, events: [] }),
      });
    });

    await page.route(`**/v1/safety/calls/${secondaryCall.callId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ call_id: secondaryCall.callId, safety_state: "NONE", safety_signals: [] }),
      });
    });

    await page.route(`**/v1/svi/calls/${secondaryCall.callId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ call_id: secondaryCall.callId, score: 40, band: "MODERATE", trend: "STABLE" }),
      });
    });

    await page.route(`**/v1/operator/calls/${secondaryCall.callId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          call_id: secondaryCall.callId,
          ownership_state: "AI_ASSISTED",
          handoff_status: "AVAILABLE",
          adaptive_paused: false,
        }),
      });
    });

    await page.route(`**/v1/operator/calls/${secondaryCall.callId}/notes`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ notes: [] }),
      });
    });
  }

  // Knowledge status & sources endpoints
  await page.route("**/v1/knowledge/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "HEALTHY",
        corpus_size: 8,
        active_documents: 8,
        total_chunks: 18,
        index_status: "READY",
        last_ingestion: new Date().toISOString(),
      }),
    });
  });

  await page.route("**/v1/knowledge/sources", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        sources: [
          {
            source_id: "doc-tn-scholarship",
            title: "Tamil Nadu Higher Education Welfare Scheme",
            authority_tier: 1,
            publisher: "Government of Tamil Nadu",
            jurisdiction: "TAMIL_NADU",
            status: "CURRENT",
            version: "2.1",
            source_date: "2024-04-01",
          },
        ],
      }),
    });
  });
}

test.describe("Phase 10: Legal / Policy RAG — Governed, Citation-First Knowledge Retrieval", () => {
  test("renders knowledge support panel with controls, filters, and disclaimer", async ({
    page,
  }) => {
    await setupMockCallWithKnowledge(page);
    await page.goto("/calls");

    // 1. Verify Knowledge Support Panel is visible
    const knowledgePanel = page.locator('[data-testid="knowledge-panel"]');
    await expect(knowledgePanel).toBeVisible();
    await expect(knowledgePanel).toContainText("Legal & Policy Knowledge RAG");

    // 2. Verify controls: query input, search button, jurisdiction, language, current-only toggle
    await expect(page.locator('[data-testid="knowledge-query-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="knowledge-search-button"]')).toBeVisible();
    await expect(page.locator('[data-testid="knowledge-jurisdiction-filter"]')).toBeVisible();
    await expect(page.locator('[data-testid="knowledge-language-filter"]')).toBeVisible();
    await expect(page.locator('[data-testid="knowledge-current-only-toggle"]')).toBeVisible();

    // 3. Verify status badge initially displays READY
    const statusBadge = page.locator('[data-testid="knowledge-status-badge"]');
    await expect(statusBadge).toBeVisible();
    await expect(statusBadge).toContainText("READY");

    // 4. Verify Legal / Operational Disclaimer banner is present
    const disclaimer = page.locator('[data-testid="knowledge-disclaimer"]');
    await expect(disclaimer).toBeVisible();
    await expect(disclaimer).toContainText("Retrieved legal and policy information is provided as source-grounded operational support");
  });

  test("executes manual search and displays grounded source cards, AI summary, and citation badges", async ({
    page,
  }) => {
    await setupMockCallWithKnowledge(page);

    // Mock search response for grounded query
    await page.route("**/v1/knowledge/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          query: "scholarship eligibility criteria",
          jurisdiction: "TAMIL_NADU",
          status: "GROUNDED",
          total_found: 2,
          results: [
            {
              chunk_id: "chk-tn-01",
              document_id: "doc-tn-scholarship",
              title: "TN Higher Education Scholarship Guidelines 2024",
              publisher: "Tamil Nadu Dept of Higher Education",
              authority_tier: 1,
              jurisdiction: "TAMIL_NADU",
              version: "2.1",
              source_date: "2024-04-01",
              effective_status: "CURRENT",
              excerpt: "Eligible students from annual household incomes below Rs. 2,50,000 shall receive 100% tuition waiver.",
              relevance_score: 0.94,
              citation: {
                citation_id: "cit-tn-001-sec4",
                source_id: "doc-tn-scholarship",
                section_page: "Section 4.1",
                text_hash: "sha256-abc12345",
                url: "https://tn.gov.in/schemes/scholarship-2024",
              },
              source_url: "https://tn.gov.in/schemes/scholarship-2024",
            },
            {
              chunk_id: "chk-central-02",
              document_id: "doc-central-postmatric",
              title: "Central Post-Matric Support Framework",
              publisher: "Ministry of Social Justice & Empowerment",
              authority_tier: 2,
              jurisdiction: "CENTRAL",
              version: "1.0",
              source_date: "2023-11-15",
              effective_status: "CURRENT",
              excerpt: "Central assistance is provided in complement with state education concessions.",
              relevance_score: 0.81,
              citation: {
                citation_id: "cit-cen-002-sec2",
                source_id: "doc-central-postmatric",
                section_page: "Clause 2",
                text_hash: "sha256-def67890",
              },
            },
          ],
          ai_summary: "Eligible students with household income below Rs. 2,50,000 receive 100% tuition waiver under Tamil Nadu Guidelines [cit:cit-tn-001-sec4]. Central assistance complements this concession [cit:cit-cen-002-sec2].",
          citations: [
            { citation_id: "cit-tn-001-sec4", source_id: "doc-tn-scholarship", section_page: "Section 4.1" },
            { citation_id: "cit-cen-002-sec2", source_id: "doc-central-postmatric", section_page: "Clause 2" },
          ],
          has_conflicts: false,
          has_stale_sources: false,
          requires_human_review: false,
        }),
      });
    });

    await page.goto("/calls");

    // Fill search input and submit
    const searchInput = page.locator('[data-testid="knowledge-query-input"]');
    await searchInput.fill("scholarship eligibility criteria");
    await page.click('[data-testid="knowledge-search-button"]');

    // Verify status badge updates to GROUNDED
    const statusBadge = page.locator('[data-testid="knowledge-status-badge"]');
    await expect(statusBadge).toContainText("GROUNDED");

    // Verify results count
    const countBadge = page.locator('[data-testid="knowledge-results-count"]');
    await expect(countBadge).toContainText("2 sources");

    // Verify AI Summary card
    const aiSummary = page.locator('[data-testid="knowledge-ai-summary"]');
    await expect(aiSummary).toBeVisible();
    await expect(aiSummary).toContainText("100% tuition waiver under Tamil Nadu Guidelines");
    await expect(aiSummary).toContainText("[cit:cit-tn-001-sec4]");

    // Verify Source Cards rendering
    const sourceCards = page.locator('[data-testid="knowledge-source-card"]');
    await expect(sourceCards).toHaveCount(2);

    // Check first card details
    const firstCard = sourceCards.first();
    await expect(firstCard.locator('[data-testid="source-card-title"]')).toContainText("TN Higher Education Scholarship Guidelines 2024");
    await expect(firstCard.locator('[data-testid="source-card-publisher"]')).toContainText("Tamil Nadu Dept of Higher Education");
    await expect(firstCard.locator('[data-testid="source-card-tier"]')).toContainText("Tier 1");
    await expect(firstCard.locator('[data-testid="source-card-jurisdiction"]')).toContainText("TAMIL_NADU");
    await expect(firstCard.locator('[data-testid="source-card-status"]')).toContainText("CURRENT");
    await expect(firstCard.locator('[data-testid="source-card-section"]')).toContainText("Sec: Section 4.1");
    await expect(firstCard.locator('[data-testid="source-card-date"]')).toContainText("Effective: 2024-04-01");
    await expect(firstCard.locator('[data-testid="source-card-excerpt"]')).toContainText("100% tuition waiver");
    await expect(firstCard.locator('[data-testid="source-card-citation"]')).toContainText("cit:cit-tn-0");
  });

  test("saves knowledge summary and citation into operator notes with citation reference", async ({
    page,
  }) => {
    await setupMockCallWithKnowledge(page);

    await page.route("**/v1/knowledge/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          query: "distress relief provisions",
          jurisdiction: "TAMIL_NADU",
          status: "GROUNDED",
          total_found: 1,
          results: [
            {
              chunk_id: "chk-relief-01",
              document_id: "doc-distress-relief",
              title: "Tamil Nadu Emergency Relief Scheme",
              publisher: "Disaster Management Authority",
              authority_tier: 1,
              jurisdiction: "TAMIL_NADU",
              version: "3.0",
              source_date: "2024-01-01",
              effective_status: "CURRENT",
              excerpt: "Immediate financial and lodging assistance is granted to vulnerable applicants.",
              relevance_score: 0.92,
              citation: {
                citation_id: "cit-relief-001",
                source_id: "doc-distress-relief",
                section_page: "Clause 3(a)",
              },
            },
          ],
          ai_summary: "Immediate financial and lodging assistance is granted to vulnerable applicants [cit:cit-relief-001].",
          citations: [{ citation_id: "cit-relief-001", source_id: "doc-distress-relief", section_page: "Clause 3(a)" }],
          has_conflicts: false,
          has_stale_sources: false,
          requires_human_review: false,
        }),
      });
    });

    await page.goto("/calls");

    // Run search
    await page.locator('[data-testid="knowledge-query-input"]').fill("distress relief provisions");
    await page.click('[data-testid="knowledge-search-button"]');

    // Click 'Save to Notes' on the AI summary
    const saveNoteButton = page.locator('[data-testid="save-knowledge-note-button"]');
    await expect(saveNoteButton).toBeVisible();
    await saveNoteButton.click();

    // Open Notes modal to view recorded notes
    const notesButton = page.locator('[data-testid="add-note-button"]');
    await notesButton.click();

    // Verify note is recorded with citation reference badge
    const notesList = page.locator('[data-testid="notes-list"]');
    await expect(notesList).toBeVisible();
    await expect(notesList).toContainText("[Knowledge Summary]");
    await expect(notesList).toContainText("Immediate financial and lodging assistance");

    const citationBadge = page.locator('[data-testid="note-citation-ref"]');
    await expect(citationBadge).toBeVisible();
    await expect(citationBadge).toContainText("citation:cit-relief-001");
  });

  test("displays conflict alert banner when conflicting policy sources are detected", async ({
    page,
  }) => {
    await setupMockCallWithKnowledge(page);

    await page.route("**/v1/knowledge/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          query: "stipend monthly amount",
          jurisdiction: "CENTRAL",
          status: "CONFLICT",
          total_found: 2,
          results: [
            {
              chunk_id: "chk-conf-1",
              title: "Policy Scheme Order 2024",
              publisher: "Central Ministry",
              authority_tier: 1,
              jurisdiction: "CENTRAL",
              version: "2.0",
              source_date: "2024-01-01",
              effective_status: "CURRENT",
              excerpt: "Monthly stipend is fixed at Rs. 5,000 per beneficiary.",
              relevance_score: 0.9,
              citation: { citation_id: "cit-ord-2024", source_id: "doc-ord-2024" },
            },
            {
              chunk_id: "chk-conf-2",
              title: "State Addendum Circular 2024",
              publisher: "State Directorate",
              authority_tier: 2,
              jurisdiction: "TAMIL_NADU",
              version: "1.0",
              source_date: "2024-02-01",
              effective_status: "CURRENT",
              excerpt: "Monthly stipend for state residents is augmented to Rs. 7,500.",
              relevance_score: 0.88,
              citation: { citation_id: "cit-add-2024", source_id: "doc-add-2024" },
            },
          ],
          ai_summary: "Conflicting stipend rates detected between Central order (Rs. 5,000) and State addendum (Rs. 7,500).",
          citations: [{ citation_id: "cit-ord-2024" }, { citation_id: "cit-add-2024" }],
          conflict_detected: true,
          conflicting_sources: [
            {
              description: "Discrepancy detected in stipulated monthly benefit amount (Rs. 5,000 vs Rs. 7,500).",
              resolution: "Tier 1 Central order takes statutory precedence",
            },
          ],
          requires_human_review: true,
        }),
      });
    });

    await page.goto("/calls");

    await page.locator('[data-testid="knowledge-query-input"]').fill("stipend monthly amount");
    await page.click('[data-testid="knowledge-search-button"]');

    // Conflict banner must be visible
    const conflictBanner = page.locator('[data-testid="knowledge-conflict-banner"]');
    await expect(conflictBanner).toBeVisible();
    await expect(conflictBanner).toContainText("SOURCE CONFLICT DETECTED");
    await expect(conflictBanner).toContainText("Discrepancy detected in stipulated monthly benefit amount");
    await expect(conflictBanner).toContainText("Tier 1 Central order takes statutory precedence");
  });

  test("displays stale source alert banner when superseded/outdated source is returned", async ({
    page,
  }) => {
    await setupMockCallWithKnowledge(page);

    await page.route("**/v1/knowledge/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          query: "archived welfare guidelines",
          jurisdiction: "ALL",
          status: "GROUNDED",
          total_found: 1,
          results: [
            {
              chunk_id: "chk-old-01",
              title: "Old Welfare Circular 2019",
              publisher: "Welfare Board",
              authority_tier: 2,
              jurisdiction: "CENTRAL",
              version: "1.0",
              source_date: "2019-01-01",
              effective_status: "EXPIRED",
              excerpt: "Applicants must submit paper forms at district headquarters.",
              relevance_score: 0.75,
              citation: { citation_id: "cit-old-01" },
            },
          ],
          ai_summary: "Guidelines under 2019 circular [cit:cit-old-01].",
          citations: [{ citation_id: "cit-old-01" }],
          requires_human_review: true,
        }),
      });
    });

    await page.goto("/calls");

    await page.locator('[data-testid="knowledge-query-input"]').fill("archived welfare guidelines");
    await page.click('[data-testid="knowledge-search-button"]');

    // Stale banner must be visible
    const staleBanner = page.locator('[data-testid="knowledge-stale-banner"]');
    await expect(staleBanner).toBeVisible();
    await expect(staleBanner).toContainText("SOURCE MAY BE OUTDATED");
    await expect(staleBanner).toContainText("One or more retrieved guidelines are superseded or past their effective sunset period");
  });

  test("shows NO_RELIABLE_SOURCE_FOUND notice when ungrounded query yields no sources", async ({
    page,
  }) => {
    await setupMockCallWithKnowledge(page);

    await page.route("**/v1/knowledge/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          query: "unrelated fantasy story topic",
          jurisdiction: "ALL",
          status: "NO_RELIABLE_SOURCE_FOUND",
          total_found: 0,
          results: [],
          ai_summary: "",
          citations: [],
          conflict_detected: false,
          requires_human_review: false,
        }),
      });
    });

    await page.goto("/calls");

    await page.locator('[data-testid="knowledge-query-input"]').fill("unrelated fantasy story topic");
    await page.click('[data-testid="knowledge-search-button"]');

    // Verify status badge
    const statusBadge = page.locator('[data-testid="knowledge-status-badge"]');
    await expect(statusBadge).toContainText("NO_RELIABLE_SOURCE_FOUND");

    // Verify zero source notice is visible
    const noSourceNotice = page.locator('[data-testid="knowledge-no-source-notice"]');
    await expect(noSourceNotice).toBeVisible();
    await expect(noSourceNotice).toContainText("NO RELIABLE SOURCE FOUND");
    await expect(noSourceNotice).toContainText("General model guesswork is strictly blocked");

    // AI summary card must NOT be displayed
    const aiSummary = page.locator('[data-testid="knowledge-ai-summary"]');
    await expect(aiSummary).not.toBeVisible();
  });

  test("timeline filters include KNOWLEDGE category with dedicated pill and coloring", async ({
    page,
  }) => {
    await setupMockCallWithKnowledge(page);
    await page.goto("/calls");

    // Find filter pills in Event Timeline
    const knowledgeFilterPill = page.locator('[data-testid="timeline-filter-KNOWLEDGE"]');
    await expect(knowledgeFilterPill).toBeVisible();
    await expect(knowledgeFilterPill).toContainText("KNOWLEDGE");

    // Click Knowledge filter pill
    await knowledgeFilterPill.click();

    // Verify timeline displays KNOWLEDGE events
    const timelineEvents = page.locator('[data-testid="timeline-event-item"]');
    await expect(timelineEvents.first()).toBeVisible();
    await expect(timelineEvents.first()).toContainText("KNOWLEDGE_SEARCH_STARTED");
  });

  test("switching calls cleanly isolates knowledge state and clears prior search results", async ({
    page,
  }) => {
    const primary = { callId: "call-rag-01", callerNumber: "+91******1111" };
    const secondary = { callId: "call-rag-02", callerNumber: "+91******2222" };

    await setupMockCallWithKnowledge(page, primary, secondary);

    await page.route("**/v1/knowledge/search", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          query: "tamil nadu scheme",
          jurisdiction: "TAMIL_NADU",
          status: "GROUNDED",
          total_found: 1,
          results: [
            {
              chunk_id: "chk-01",
              title: "TN Scheme Card",
              publisher: "TN Govt",
              authority_tier: 1,
              jurisdiction: "TAMIL_NADU",
              version: "1.0",
              source_date: "2024-01-01",
              effective_status: "CURRENT",
              excerpt: "TN Scheme excerpt content.",
              relevance_score: 0.9,
              citation: { citation_id: "cit-01" },
            },
          ],
          ai_summary: "TN Scheme Summary.",
          citations: [{ citation_id: "cit-01" }],
          conflict_detected: false,
          requires_human_review: false,
        }),
      });
    });

    await page.goto("/calls");

    // Primary call is selected by default on load
    // Run search on primary call
    await page.locator('[data-testid="knowledge-query-input"]').fill("tamil nadu scheme");
    await page.click('[data-testid="knowledge-search-button"]');

    // Confirm search results appeared
    await expect(page.locator('[data-testid="knowledge-ai-summary"]')).toBeVisible();

    // Switch to secondary call
    const callItems = page.locator('[data-testid="call-item"]');
    await callItems.nth(1).click();

    // Knowledge results must be cleared for new call session
    await expect(page.locator('[data-testid="knowledge-ai-summary"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="knowledge-status-badge"]')).toContainText("READY");
    await expect(page.locator('[data-testid="knowledge-query-input"]')).toHaveValue("");
  });
});
