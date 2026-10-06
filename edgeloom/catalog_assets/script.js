"use strict";

const filters = document.querySelector("#filters");
if (filters) {
  const query = document.querySelector("#query");
  const protocol = document.querySelector("#protocol");
  const review = document.querySelector("#review");
  const cards = [...document.querySelectorAll("[data-device]")];
  const count = document.querySelector("#result-count");
  const empty = document.querySelector("#empty");
  const initial = new URLSearchParams(window.location.search);
  query.value = initial.get("q") || "";
  if ([...protocol.options].some((option) => option.value === initial.get("protocol"))) {
    protocol.value = initial.get("protocol");
  }
  if ([...review.options].some((option) => option.value === initial.get("review"))) {
    review.value = initial.get("review");
  }
  const update = () => {
    const words = query.value.trim().toLocaleLowerCase("en").split(/\s+/).filter(Boolean);
    let visible = 0;
    for (const card of cards) {
      const matches = words.every((word) => card.dataset.search.includes(word))
        && (!protocol.value || protocol.value === card.dataset.protocol)
        && (!review.value || card.dataset.status.split(" ").includes(review.value));
      card.hidden = !matches;
      if (matches) visible += 1;
    }
    count.textContent = `${visible} device ${visible === 1 ? "model" : "models"} indexed${visible === cards.length ? "" : " matching these filters"}`;
    empty.hidden = visible !== 0;
    const url = new URL(window.location.href);
    for (const [key, value] of [["q", query.value.trim()], ["protocol", protocol.value], ["review", review.value]]) {
      if (value) url.searchParams.set(key, value);
      else url.searchParams.delete(key);
    }
    window.history.replaceState(null, "", url);
  };
  filters.addEventListener("input", update);
  filters.addEventListener("change", update);
  filters.addEventListener("submit", (event) => { event.preventDefault(); update(); });
  filters.addEventListener("reset", (event) => {
    event.preventDefault();
    query.value = "";
    protocol.value = "";
    review.value = "";
    update();
  });
  update();
}
