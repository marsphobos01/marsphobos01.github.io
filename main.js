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

    const track = (eventName, props) => {
        if (!eventName || !window.umami || typeof window.umami.track !== "function") return;
        window.umami.track(eventName, Object.assign({
            page_path: window.location.pathname,
            referrer: document.referrer || ""
        }, props || {}));
    };

    document.addEventListener("click", (event) => {
        const link = event.target.closest("a");
        if (!link) return;

        const href = link.getAttribute("href") || "";
        const url = (() => {
            try { return new URL(href, window.location.href); }
            catch (e) { return null; }
        })();
        const label = (link.textContent || "").trim().replace(/\s+/g, " ").slice(0, 80);

        if (href.includes("Morgan-Bennett-CV.pdf")) track("cv_downloaded", { link_text: label });
        if (href.startsWith("mailto:")) track("email_clicked", { link_text: label });
        if (href === "/#contact" || href === "#contact") track("contact_clicked", { link_text: label });
        if (url && url.hostname.includes("github.com")) track("github_clicked", { link_text: label, destination: url.href });
        if (url && url.hostname.includes("linkedin.com")) track("linkedin_clicked", { link_text: label, destination: url.href });
        if (href.startsWith("/projects/")) {
            const project = href.split("/").filter(Boolean).pop() || "project";
            track("case_study_viewed", { project_name: project, destination: href });
        }
        if (url && (url.hostname.endsWith("marsphobos.com") || url.hostname === window.location.hostname) && href.startsWith("/posts/")) {
            track("blog_article_opened", { article: href.split("/").filter(Boolean).pop() || "post", destination: href });
        }
        if (url && url.hostname !== window.location.hostname && !url.hostname.includes("github.com") && !url.hostname.includes("linkedin.com")) {
            const project = link.closest(".proj, .card, .case-aside")?.querySelector(".proj-title, h1")?.textContent?.trim() || url.hostname;
            track("project_opened", { project_name: project, destination: url.href });
        }
    });

    const reveals = document.querySelectorAll(".reveal");
    if (reveals.length) {
        const io = new IntersectionObserver((entries) => {
            entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
        }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });
        reveals.forEach((el, i) => { el.style.transitionDelay = Math.min(i % 4, 3) * 70 + "ms"; io.observe(el); });
    }
})();
