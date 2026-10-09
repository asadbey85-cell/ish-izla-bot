(() => {
  const form = document.querySelector("#focus-form");
  const clock = document.querySelector("#focus-clock");
  const duration = document.querySelector("#focus-duration");
  const startButton = document.querySelector("#focus-start");
  const pauseButton = document.querySelector("#focus-pause");
  const resetButton = document.querySelector("#focus-reset");
  if (!form || !clock || !duration || !startButton || !pauseButton || !resetButton) return;

  let remaining = Number(duration.value) * 60;
  let deadline = 0;
  let interval = null;

  const render = () => {
    const minutes = Math.floor(remaining / 60);
    const seconds = remaining % 60;
    clock.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  };

  const stop = () => {
    window.clearInterval(interval);
    interval = null;
    pauseButton.disabled = true;
    duration.disabled = false;
  };

  const finish = async () => {
    stop();
    startButton.disabled = true;
    startButton.textContent = "Saqlanmoqda...";
    const minutes = Number(duration.value);
    const body = new URLSearchParams({
      action: "focus",
      minutes: String(minutes),
      csrf_token: form.dataset.csrf,
    });
    try {
      const response = await fetch(form.action, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
        credentials: "same-origin",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      window.location.reload();
    } catch (error) {
      startButton.disabled = false;
      startButton.textContent = "Qayta saqlash";
      window.alert("Fokus vaqti saqlanmadi. Internetni tekshirib, qayta urinib ko‘ring.");
    }
  };

  const tick = () => {
    remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
    render();
    if (remaining === 0) finish();
  };

  duration.addEventListener("change", () => {
    remaining = Number(duration.value) * 60;
    render();
  });
  startButton.addEventListener("click", () => {
    if (interval) return;
    deadline = Date.now() + remaining * 1000;
    duration.disabled = true;
    pauseButton.disabled = false;
    startButton.textContent = "Davom etmoqda...";
    interval = window.setInterval(tick, 250);
  });
  pauseButton.addEventListener("click", () => {
    tick();
    stop();
    startButton.textContent = "Davom ettirish";
  });
  resetButton.addEventListener("click", () => {
    stop();
    remaining = Number(duration.value) * 60;
    startButton.disabled = false;
    startButton.textContent = "Boshlash ▶";
    render();
  });
  render();
})();
