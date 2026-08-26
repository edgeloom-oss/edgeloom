document.documentElement.classList.add("js");

const menuButton = document.querySelector(".menu-toggle");
const primaryNav = document.querySelector("#primary-nav");

if (menuButton && primaryNav) {
  menuButton.addEventListener("click", () => {
    const isOpen = menuButton.getAttribute("aria-expanded") === "true";
    menuButton.setAttribute("aria-expanded", String(!isOpen));
    document.body.classList.toggle("nav-open", !isOpen);
  });

  primaryNav.addEventListener("click", (event) => {
    if (event.target instanceof HTMLAnchorElement) {
      menuButton.setAttribute("aria-expanded", "false");
      document.body.classList.remove("nav-open");
    }
  });
}

const copyNotice = document.querySelector(".copy-notice");

document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const value = button.getAttribute("data-copy") || "";
    try {
      await navigator.clipboard.writeText(value);
      button.textContent = "Copied";
      if (copyNotice) copyNotice.textContent = "Quickstart commands copied to clipboard.";
      window.setTimeout(() => {
        button.textContent = "Copy";
      }, 1800);
    } catch {
      if (copyNotice) copyNotice.textContent = "Copy failed. Select the commands manually.";
    }
  });
});
