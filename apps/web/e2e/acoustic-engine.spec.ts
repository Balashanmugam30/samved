import { test, expect, Page } from "@playwright/test";

async function setupMockCallWithAcoustic(page: Page, mockCallId = "call-acoustic-test-01") {
  // Prevent background WebSocket from racing or clearing mock state
  await page.route("**/ws/operator", (route) => route.abort());

  await page.route("**/v1/calls", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        active_calls: [
          {
            call_id: mockCallId,
            caller_masked_number: "+91******3210",
            state: "STREAMING",
            conversation_state: "LISTENING",
            current_language: "en-IN",
            duration_seconds: 60,
            provider: "exotel",
            is_active: true,
            safety_state: "NONE",
            safety_signals_count: 0,
            svi_score: 20,
            svi_band: "LOW",
            acoustic_quality: "GOOD",
            acoustic_confidence: 0.95,
            acoustic_signals_count: 1,
          },
        ],
        recent_calls: [],
      }),
    });
  });

  await page.route(`**/v1/calls/${mockCallId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: mockCallId,
        caller_masked_number: "+91******3210",
        state: "STREAMING",
        conversation_state: "LISTENING",
        current_language: "en-IN",
        safety_state: "NONE",
        safety_signals_count: 0,
        duration_seconds: 60,
        provider: "exotel",
        is_active: true,
      }),
    });
  });

  await page.route(`**/v1/calls/${mockCallId}/transcript`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: mockCallId,
        utterances: [
          {
            utterance_id: "utt-ac-001",
            speaker: "caller",
            text: "Hello, I am calling for emergency advice.",
            language: "en-IN",
            safety_flag: false,
            created_at: new Date().toISOString(),
          },
        ],
      }),
    });
  });

  await page.route(`**/v1/calls/${mockCallId}/events`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: mockCallId,
        events: [],
      }),
    });
  });

  await page.route(`**/v1/safety/calls/${mockCallId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        call_id: mockCallId,
        safety_state: "NONE",
        active_signals: [],
        acknowledged_signals: [],
        escalation_history: [],
      }),
    });
  });

  await page.route(`**/v1/svi/calls/${mockCallId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        assessment_id: "svi-ac-001",
        call_id: mockCallId,
        session_id: "sess-ac-001",
        turn_index: 1,
        score: 20,
        band: "LOW",
        trend: "INITIAL",
        delta: 0,
        assessment_completeness: 0.40,
        features: [],
        top_contributors: [],
        protective_factor_reduction: 0,
        critical_override_applied: false,
        acoustic_evidence_available: true,
        acoustic_evidence_note: "Acoustic observations: quality=GOOD, signals=PROLONGED_SILENCE_OBSERVED",
        requires_human_review: false,
        disclaimer: "Operational Prototype Priority Indicator — NOT a clinical, medical, or diagnostic score",
        evaluated_at: new Date().toISOString(),
        svi_version: "v1",
      }),
    });
  });

  await page.route(`**/v1/acoustic/calls/${mockCallId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        assessment_id: "ac-mock-001",
        call_id: mockCallId,
        session_id: "sess-ac-001",
        quality: "GOOD",
        confidence: 0.95,
        voice_activity: {
          speech_activity_ratio: 0.45,
          silence_ratio: 0.55,
          total_voiced_ms: 1800,
          total_silence_ms: 2200,
        },
        pause_metrics: {
          pause_count: 3,
          avg_pause_duration_ms: 1100.0,
          longest_pause_ms: 3200,
          sustained_silence_count: 1,
        },
        turn_metrics: {
          turn_duration_ms: 4000,
          speech_segment_duration_ms: 1800,
          turn_density: 0.45,
        },
        interruption_metrics: {
          interruption_count: 2,
          rapid_interruption_detected: true,
        },
        energy_metrics: {
          mean_energy_rms: 520.0,
          energy_variability: 0.58,
          peak_energy_rms: 980.0,
          low_signal_ratio: 0.05,
          clipping_ratio: 0.0,
        },
        pitch_metrics: {
          median_f0_hz: 185.0,
          f0_variability: 22.0,
          voiced_frame_ratio: 0.45,
        },
        operational_signals: [
          {
            code: "PROLONGED_SILENCE_OBSERVED",
            evidence: "3200ms sustained low-activity window",
            confidence: 0.95,
            threshold_applied: ">=3000ms",
          },
          {
            code: "FREQUENT_INTERRUPTION_PATTERN",
            evidence: "2 interruptions observed in active turn",
            confidence: 0.9,
            threshold_applied: ">=2 interruptions",
          },
        ],
        engine_version: "v1.0.0",
        disclaimer: "Operational support signals only. Not clinical or diagnostic.",
        evaluated_at: new Date().toISOString(),
      }),
    });
  });
}

test.describe("SAMVED Phase 6 Acoustic Analysis Engine E2E", () => {
  test("renders Acoustic Signals Panel with quality badge, metrics, and non-clinical disclaimer", async ({ page }) => {
    await setupMockCallWithAcoustic(page);
    await page.goto("/calls");

    // Click call card to select it
    await page.getByTestId("call-item").first().waitFor({ state: "visible", timeout: 10000 });
    await page.getByTestId("call-item").first().click({ force: true });

    // 1. Verify Acoustic panel exists
    const acousticPanel = page.getByTestId("acoustic-panel");
    await expect(acousticPanel).toBeVisible({ timeout: 10000 });

    // 2. Verify Acoustic Quality Badge
    const qualityBadge = page.getByTestId("acoustic-quality-badge");
    await expect(qualityBadge).toBeAttached();
    await expect(qualityBadge).toContainText("GOOD");

    // 3. Verify Confidence Indicator
    const confidence = page.getByTestId("acoustic-confidence");
    await expect(confidence).toBeAttached();
    await expect(confidence).toContainText("Conf: 95%");

    // 4. Verify Non-Clinical Disclaimer
    const disclaimer = page.getByTestId("acoustic-disclaimer");
    await expect(disclaimer).toBeAttached();
    await expect(disclaimer).toContainText("Operational support signals only. Not clinical or diagnostic.");

    // 5. Verify Metrics Grid
    const speechRatio = page.getByTestId("acoustic-speech-ratio");
    await expect(speechRatio).toBeAttached();
    await expect(speechRatio).toContainText("45%");

    const longestPause = page.getByTestId("acoustic-longest-pause");
    await expect(longestPause).toBeAttached();
    await expect(longestPause).toContainText("3200ms");

    const interruptions = page.getByTestId("acoustic-interruptions");
    await expect(interruptions).toBeAttached();
    await expect(interruptions).toContainText("2");

    const energyVar = page.getByTestId("acoustic-energy-var");
    await expect(energyVar).toBeAttached();
    await expect(energyVar).toContainText("CV 0.58");

    // 6. Verify Operational Signals List and Chips
    const signalsList = page.getByTestId("acoustic-signals-list");
    await expect(signalsList).toBeAttached();
    await expect(signalsList).toContainText("PROLONGED_SILENCE_OBSERVED");
    await expect(signalsList).toContainText("FREQUENT_INTERRUPTION_PATTERN");
  });

  test("renders Acoustic Lab button and opens Acoustic Simulation Lab modal", async ({ page }) => {
    await page.goto("/calls");

    // 1. Verify Acoustic Lab button in header
    const acousticLabBtn = page.getByTestId("open-acoustic-lab");
    await expect(acousticLabBtn).toBeAttached();
    await expect(acousticLabBtn).toContainText("Acoustic Lab");

    // 2. Click to open modal
    await acousticLabBtn.click();

    // 3. Verify modal header and container
    const modal = page.getByTestId("acoustic-lab-modal");
    await expect(modal).toBeVisible({ timeout: 5000 });
    await expect(page.locator("text=Acoustic Analysis Simulation Lab")).toBeVisible();

    // 4. Verify ethical boundary disclaimer text
    await expect(page.locator("text=Operational Support Signals Only")).toBeVisible();

    // 5. Verify preset buttons exist
    await expect(page.getByTestId("preset-normal-convo")).toBeVisible();
    await expect(page.getByTestId("preset-prolonged-silence")).toBeVisible();
    await expect(page.getByTestId("preset-frequent-interruptions")).toBeVisible();
    await expect(page.getByTestId("preset-high-energy-var")).toBeVisible();
    await expect(page.getByTestId("preset-low-quality")).toBeVisible();
    await expect(page.getByTestId("preset-insufficient")).toBeVisible();

    // 6. Verify evaluate button exists
    const evalBtn = page.getByTestId("run-acoustic-eval");
    await expect(evalBtn).toBeAttached();
    await expect(evalBtn).toContainText("Run Acoustic Evaluation");

    // 7. Close modal
    await page.getByTestId("close-acoustic-lab").click();
    await expect(modal).not.toBeVisible();
  });

  test("evaluates synthetic parameters in simulation lab and displays operational signals", async ({ page }) => {
    // Intercept evaluate endpoint
    await page.route("**/v1/acoustic/evaluate", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          assessment_id: "sim-eval-001",
          call_id: "sim-acoustic-lab",
          session_id: "sim-acoustic-sess",
          quality: "GOOD",
          confidence: 0.90,
          voice_activity: {
            speech_activity_ratio: 0.25,
            silence_ratio: 0.75,
            total_voiced_ms: 1500,
            total_silence_ms: 4500,
          },
          pause_metrics: {
            pause_count: 2,
            avg_pause_duration_ms: 2250.0,
            longest_pause_ms: 3500,
            sustained_silence_count: 1,
          },
          turn_metrics: {
            turn_duration_ms: 6000,
            speech_segment_duration_ms: 1500,
            turn_density: 0.25,
          },
          interruption_metrics: {
            interruption_count: 0,
            rapid_interruption_detected: false,
          },
          energy_metrics: {
            mean_energy_rms: 350.0,
            energy_variability: 0.20,
            peak_energy_rms: 600.0,
            low_signal_ratio: 0.0,
            clipping_ratio: 0.0,
          },
          pitch_metrics: {
            median_f0_hz: 165.0,
            f0_variability: 15.0,
            voiced_frame_ratio: 0.25,
          },
          operational_signals: [
            {
              code: "PROLONGED_SILENCE_OBSERVED",
              evidence: "3500ms sustained low-activity window",
              confidence: 0.90,
              threshold_applied: ">=3000ms",
            },
          ],
          engine_version: "v1.0.0",
          disclaimer: "Operational support signals only. Not clinical or diagnostic.",
          evaluated_at: new Date().toISOString(),
        }),
      });
    });

    await page.goto("/calls");
    await page.getByTestId("open-acoustic-lab").click();

    // Select Prolonged Silence preset
    await page.getByTestId("preset-prolonged-silence").click();

    // Run evaluation
    await page.getByTestId("run-acoustic-eval").click();

    // Verify results panel appeared
    const resultPanel = page.getByTestId("acoustic-lab-result");
    await expect(resultPanel).toBeVisible({ timeout: 5000 });

    // Verify PROLONGED_SILENCE_OBSERVED is displayed in results
    await expect(resultPanel).toContainText("PROLONGED_SILENCE_OBSERVED");
    await expect(resultPanel).toContainText("3500ms sustained low-activity window");
    await expect(resultPanel).toContainText("Confidence: 90%");
  });
});
