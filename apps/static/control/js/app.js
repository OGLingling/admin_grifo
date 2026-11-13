document.addEventListener("DOMContentLoaded", () => {
  const menuButton = document.querySelector(".menu-button");
  const sidebar = document.querySelector(".sidebar");
  if (menuButton && sidebar) {
    menuButton.addEventListener("click", () => {
      const expanded = menuButton.getAttribute("aria-expanded") === "true";
      menuButton.setAttribute("aria-expanded", String(!expanded));
      sidebar.classList.toggle("sidebar-open", !expanded);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        sidebar.classList.remove("sidebar-open");
        menuButton.setAttribute("aria-expanded", "false");
      }
    });
  }
  document.querySelectorAll(".message > button").forEach((button) => {
    button.addEventListener("click", () => button.closest(".message")?.remove());
  });
  const productSelect = document.querySelector("#id_product");
  const priceInput = document.querySelector("#id_unit_price");
  if (productSelect && priceInput) {
    const syncPrice = () => {
      const option = productSelect.selectedOptions[0];
      if (option?.dataset.unitPrice) priceInput.value = option.dataset.unitPrice;
    };
    productSelect.addEventListener("change", syncPrice);
    syncPrice();
  }
});
