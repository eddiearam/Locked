const form = document.getElementById("goal-form");
const resultEl = document.getElementById("result");
const dbNoteEl = document.getElementById("db-note");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  resultEl.hidden = true;
  dbNoteEl.hidden = true;

  const body = {
    user_id: Number(document.getElementById("user_id").value),
    screen_on_time_hours: Number(document.getElementById("screen_on_time_hours").value),
    target_hours: Number(document.getElementById("target_hours").value),
  };

  try {
    const response = await fetch("/api/check-goal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json();

    if (!response.ok || !data.success) {
      resultEl.textContent = data.error || "Request failed";
      resultEl.className = "result fail";
      resultEl.hidden = false;
      return;
    }

    const completed = Boolean(data.goal_completed);
    resultEl.textContent = completed ? "✅ Goal completed" : "❌ Goal not completed";
    resultEl.className = completed ? "result ok" : "result fail";
    resultEl.hidden = false;

    dbNoteEl.textContent = data.observation_saved
      ? `Observation saved to the database (id ${data.observation_id}).`
      : "Observation was not saved.";
    dbNoteEl.hidden = false;
  } catch (error) {
    resultEl.textContent = "Could not reach the server.";
    resultEl.className = "result fail";
    resultEl.hidden = false;
  }
});
