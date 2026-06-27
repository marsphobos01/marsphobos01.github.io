// Shared site interactions (all pages)
(function () {
    const header = document.getElementById("header");
    if (header) {
        const onScroll = () => header.classList.toggle("solid", window.scrollY > 20);
        onScroll();
        window.addEventListener("scroll", onScroll, { passive: true });
    }

    const menuToggle = document.getElementById("menuToggle");
    const navLinks = document.getElementById("navLinks");
    if (menuToggle && navLinks) {
        const setMenu = (open) => {
            navLinks.classList.toggle("open", open);
            menuToggle.classList.toggle("open", open);
            menuToggle.setAttribute("aria-expanded", open ? "true" : "false");
            document.body.classList.toggle("nav-open", open);
        };
        menuToggle.addEventListener("click", () => setMenu(!navLinks.classList.contains("open")));
        navLinks.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => setMenu(false)));
    }

    const year = document.getElementById("year");
    if (year) year.textContent = new Date().getFullYear();

    const reveals = document.querySelectorAll(".reveal");
    if (reveals.length) {
        const io = new IntersectionObserver((entries) => {
            entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
        }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });
        reveals.forEach((el, i) => { el.style.transitionDelay = Math.min(i % 4, 3) * 70 + "ms"; io.observe(el); });
    }
})();
