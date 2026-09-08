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

// Display-only condition -> icon lookup. `core.py`'s `condition` strings
// (see `sources/weather.py`'s WMO code descriptions) are presentation-
// agnostic by design, so this mapping lives entirely in the frontend.
const CONDITION_ICONS = {
  "Clear sky": "\u2600\ufe0f",
  "Mainly clear": "\ud83c\udf24\ufe0f",
  "Partly cloudy": "\u26c5",
  "Overcast": "\u2601\ufe0f",
  "Fog": "\ud83c\udf2b\ufe0f",
  "Depositing rime fog": "\ud83c\udf2b\ufe0f",
  "Light drizzle": "\ud83c\udf26\ufe0f",
  "Moderate drizzle": "\ud83c\udf26\ufe0f",
  "Dense drizzle": "\ud83c\udf26\ufe0f",
  "Light freezing drizzle": "\ud83c\udf28\ufe0f",
  "Dense freezing drizzle": "\ud83c\udf28\ufe0f",
  "Slight rain": "\ud83c\udf27\ufe0f",
  "Moderate rain": "\ud83c\udf27\ufe0f",
  "Heavy rain": "\ud83c\udf27\ufe0f",
  "Light freezing rain": "\ud83c\udf28\ufe0f",
  "Heavy freezing rain": "\ud83c\udf28\ufe0f",
  "Slight snow fall": "\ud83c\udf28\ufe0f",
  "Moderate snow fall": "\ud83c\udf28\ufe0f",
  "Heavy snow fall": "\ud83c\udf28\ufe0f",
  "Snow grains": "\ud83c\udf28\ufe0f",
  "Slight rain showers": "\ud83c\udf27\ufe0f",
  "Moderate rain showers": "\ud83c\udf27\ufe0f",
  "Violent rain showers": "\ud83c\udf27\ufe0f",
  "Slight snow showers": "\ud83c\udf28\ufe0f",
  "Heavy snow showers": "\ud83c\udf28\ufe0f",
  "Thunderstorm": "\u26c8\ufe0f",
  "Thunderstorm with slight hail": "\u26c8\ufe0f",
  "Thunderstorm with heavy hail": "\u26c8\ufe0f",
};
const DEFAULT_CONDITION_ICON = "\ud83c\udf24\ufe0f";

function conditionIcon(condition) {
  return CONDITION_ICONS[condition] || DEFAULT_CONDITION_ICON;
}

// "Low"/"Medium"/"High"/"Unknown" -> rain-badge color token.
function rainLevel(rainChance) {
  const level = (rainChance || "").toLowerCase();
  return level === "low" || level === "medium" || level === "high" ? level : "medium";
}

function renderWeather(el, data) {
  el.dataset.state = "loaded";
  if (!data.days.length) {
    el.textContent = "No forecast data available.";
    return;
  }
  el.innerHTML = "";
  const list = document.createElement("ul");
  list.className = "weather-list";
  for (const day of data.days) {
    const item = document.createElement("li");
    item.className = "weather-day";

    const icon = document.createElement("span");
    icon.className = "weather-day-icon";
    icon.textContent = conditionIcon(day.condition);
    icon.setAttribute("aria-hidden", "true");
    item.appendChild(icon);

    const main = document.createElement("div");
    main.className = "weather-day-main";

    const dateEl = document.createElement("span");
    dateEl.className = "weather-day-date";
    dateEl.textContent = day.date;
    main.appendChild(dateEl);

    const temps = document.createElement("span");
    temps.className = "weather-day-temps";
    temps.textContent = `${day.condition} \u2014 High ${day.high_temp_c}\u00b0C / Low ${day.low_temp_c}\u00b0C`;
    main.appendChild(temps);

    item.appendChild(main);

    const badge = document.createElement("span");
    badge.className = "rain-badge";
    badge.dataset.level = rainLevel(day.rain_chance);
    badge.textContent = `Rain: ${day.rain_chance}`;
    item.appendChild(badge);

    list.appendChild(item);
  }
  el.appendChild(list);
}

function renderMediaList(el, items, buildItem, emptyMessage) {
  el.dataset.state = "loaded";
  if (!items.length) {
    el.textContent = emptyMessage;
    return;
  }
  el.innerHTML = "";
  const list = document.createElement("ul");
  list.className = "media-list";
  for (const data of items) {
    list.appendChild(buildItem(data));
  }
  el.appendChild(list);
}

function buildMediaThumb(imageUrl, altText, placeholderIcon) {
  if (imageUrl) {
    const img = document.createElement("img");
    img.className = "media-thumb";
    img.src = imageUrl;
    img.alt = altText;
    img.loading = "lazy";
    return img;
  }
  const placeholder = document.createElement("div");
  placeholder.className = "media-thumb media-thumb-placeholder";
  placeholder.textContent = placeholderIcon;
  placeholder.setAttribute("aria-hidden", "true");
  return placeholder;
}

function renderFood(el, data) {
  renderMediaList(
    el,
    data.items,
    (item) => {
      const li = document.createElement("li");
      li.className = "media-item";
      li.appendChild(buildMediaThumb(item.image_url, item.name, "\ud83c\udf74"));

      const body = document.createElement("div");
      body.className = "media-body";
      const title = document.createElement("div");
      title.className = "media-title";
      title.textContent = item.name;
      body.appendChild(title);
      const subtitle = document.createElement("div");
      subtitle.className = "media-subtitle";
      subtitle.textContent = item.restaurant;
      body.appendChild(subtitle);
      li.appendChild(body);

      return li;
    },
    "No food recommendations available."
  );
}

function renderBooks(el, data) {
  renderMediaList(
    el,
    data.items,
    (item) => {
      const li = document.createElement("li");
      li.className = "media-item";
      li.appendChild(buildMediaThumb(item.cover_url, item.title, "\ud83d\udcda"));

      const body = document.createElement("div");
      body.className = "media-body";
      const title = document.createElement("div");
      title.className = "media-title";
      title.textContent = item.title;
      body.appendChild(title);
      const subtitle = document.createElement("div");
      subtitle.className = "media-subtitle";
      subtitle.textContent = item.author;
      body.appendChild(subtitle);
      const description = document.createElement("div");
      description.className = "media-description";
      description.textContent = item.description;
      body.appendChild(description);
      li.appendChild(body);

      return li;
    },
    "No book recommendations available."
  );
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
