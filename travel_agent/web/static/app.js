// Vanilla JS driving the single-page UI. Each feature section is
// fetched and rendered independently so a slow/failed food or books
// call never blocks the weather section (or each other).

const themeToggle = document.getElementById("theme-toggle");

// The initial theme is already applied by the inline <script> in
// <head> (before first paint); this handler only manages toggling
// and persisting the choice thereafter.
themeToggle.addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme");
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
});

const form = document.getElementById("explore-form");
const cityInput = document.getElementById("city-input");
const welcomeMessage = document.getElementById("welcome-message");

const sections = {
  weather: document.querySelector("#weather-section .section-body"),
  food: document.querySelector("#food-section .section-body"),
  books: document.querySelector("#books-section .section-body"),
};

function setLoading(el) {
  el.dataset.state = "loading";
  el.textContent = "Loading...";
}

function setError(el, message) {
  el.dataset.state = "error";
  el.textContent = `Error: ${message}`;
}

async function fetchJson(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || `Request failed with status ${response.status}`);
  }
  return data;
}

function renderWeather(el, data) {
  el.dataset.state = "loaded";
  if (!data.days.length) {
    el.textContent = "No forecast data available.";
    return;
  }
  el.innerHTML = "";
  const list = document.createElement("ul");
  for (const day of data.days) {
    const item = document.createElement("li");
    const avg =
      day.avg_temp_9am_9pm_c !== null && day.avg_temp_9am_9pm_c !== undefined
        ? `${day.avg_temp_9am_9pm_c.toFixed(1)}\u00b0C`
        : "N/A";
    item.textContent =
      `${day.date}: High ${day.high_temp_c}\u00b0C / Low ${day.low_temp_c}\u00b0C, ` +
      `Avg 9am-9pm ${avg}, ${day.condition}, Rain chance: ${day.rain_chance}`;
    list.appendChild(item);
  }
  el.appendChild(list);
}

function renderFood(el, data) {
  el.dataset.state = "loaded";
  if (!data.items.length) {
    el.textContent = "No food recommendations available.";
    return;
  }
  el.innerHTML = "";
  const list = document.createElement("ul");
  for (const item of data.items) {
    const li = document.createElement("li");
    li.textContent = `${item.name} — ${item.restaurant}`;
    list.appendChild(li);
  }
  el.appendChild(list);
}

function renderBooks(el, data) {
  el.dataset.state = "loaded";
  if (!data.items.length) {
    el.textContent = "No book recommendations available.";
    return;
  }
  el.innerHTML = "";
  const list = document.createElement("ul");
  for (const item of data.items) {
    const li = document.createElement("li");
    li.textContent = `${item.title} by ${item.author} — ${item.description}`;
    list.appendChild(li);
  }
  el.appendChild(list);
}

async function loadWelcome(city) {
  try {
    const data = await fetchJson(`/api/welcome?city=${encodeURIComponent(city)}`);
    welcomeMessage.textContent = data.message;
  } catch (err) {
    welcomeMessage.textContent = "";
  }
}

async function loadWeather(city) {
  setLoading(sections.weather);
  try {
    const data = await fetchJson(`/api/weather?city=${encodeURIComponent(city)}`);
    renderWeather(sections.weather, data);
  } catch (err) {
    setError(sections.weather, err.message);
  }
}

async function loadFood(city) {
  setLoading(sections.food);
  try {
    const data = await fetchJson(`/api/food?city=${encodeURIComponent(city)}`);
    renderFood(sections.food, data);
  } catch (err) {
    setError(sections.food, err.message);
  }
}

async function loadBooks(city) {
  setLoading(sections.books);
  try {
    const data = await fetchJson(`/api/books?city=${encodeURIComponent(city)}`);
    renderBooks(sections.books, data);
  } catch (err) {
    setError(sections.books, err.message);
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const city = cityInput.value.trim();
  if (!city) {
    return;
  }

  // Fire all four requests concurrently; each has its own try/catch so
  // one failure never blocks the others.
  loadWelcome(city);
  loadWeather(city);
  loadFood(city);
  loadBooks(city);
});
