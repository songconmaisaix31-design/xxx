(() => {
  "use strict";

  const root = document.documentElement;
  const body = document.body;
  const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  const finePointerQuery = window.matchMedia("(hover: hover) and (pointer: fine)");

  const motionSelectors = [
    ".flash",
    ".home-hero",
    ".hero-copy > *",
    ".protocol-panel > *",
    ".principle-list article",
    ".home-launchpad-heading > *",
    ".home-path",
    ".auth-story > *",
    ".auth-form-panel > *",
    ".page-heading > *",
    ".form-page-heading > *",
    ".form-section",
    ".source-card",
    ".profile-hero > *",
    ".section-heading-line > *",
    ".tag-card",
    ".match-card",
    ".match-flow-heading > *",
    ".match-ready-card > *",
    ".match-rules-panel > *",
    ".match-search-board",
    ".match-result > *",
    ".match-result-actions > *",
    ".inbox-row",
    ".conversation-hero > *",
    ".unlock-panel",
    ".member-strip",
    ".message",
    ".toolbox > *",
    ".message-form",
    ".event-row",
    ".event-detail-hero > *",
    ".detail-panel",
    ".group-entry",
    ".coupon-panel",
    ".review-panel",
    ".applicant-row",
    ".danger-zone"
  ];

  const immediateSelectors = [
    ".site-header",
    ".home-hero",
    ".profile-hero",
    ".conversation-hero",
    ".event-detail-hero",
    ".page-heading",
    ".form-page-heading"
  ];

  const interactiveSelectors = [
    "a",
    "button",
    "summary",
    ".choice-tile",
    ".match-card",
    ".source-card",
    ".event-row",
    ".inbox-row"
  ];

  const scoreSelectors = [
    ".match-score strong",
    ".result-score strong",
    ".event-score strong",
    ".event-hero-score strong"
  ];

  const uniqueElements = (selectors) => {
    const nodes = selectors.flatMap((selector) => Array.from(document.querySelectorAll(selector)));
    return Array.from(new Set(nodes));
  };

  const isReduced = () => reducedMotionQuery.matches;

  const setViewportHeight = () => {
    const viewportHeight = window.visualViewport?.height || window.innerHeight;
    root.style.setProperty("--visual-viewport-height", `${Math.round(viewportHeight)}px`);
  };

  const setInteractionMode = () => {
    root.dataset.pointer = finePointerQuery.matches ? "fine" : "coarse";
    root.dataset.motion = isReduced() ? "reduced" : "full";
  };

  const motionKindFor = (element) => {
    if (element.matches(".message.mine")) {
      return "message-right";
    }

    if (element.matches(".message.theirs")) {
      return "message-left";
    }

    if (element.matches(".message.system")) {
      return "message-system";
    }

    if (element.matches(".tag-card, .match-card, .source-card, .detail-panel, .home-path, .match-search-board")) {
      return "card-pop";
    }

    if (element.matches(".event-row, .inbox-row, .applicant-row")) {
      return "row-slide";
    }

    if (element.matches(".protocol-panel > *, .toolbox > *")) {
      return "side-step";
    }

    if (element.matches(".hero-copy > *, .auth-story > *, .profile-hero > *")) {
      return "hero-rise";
    }

    if (element.matches(".form-section")) {
      return "section-rise";
    }

    return "soft-rise";
  };

  const prepareMotion = () => {
    const elements = uniqueElements(motionSelectors);

    elements.forEach((element, index) => {
      element.dataset.motionItem = motionKindFor(element);
      element.style.setProperty("--motion-order", String(index % 12));
    });

    return elements;
  };

  const revealMotion = (elements) => {
    if (isReduced() || !("IntersectionObserver" in window)) {
      elements.forEach((element) => element.classList.add("is-motion-visible"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return;
          }

          entry.target.classList.add("is-motion-visible");
          observer.unobserve(entry.target);
        });
      },
      {
        rootMargin: "0px 0px -7% 0px",
        threshold: 0.08
      }
    );

    elements.forEach((element) => {
      const isImmediate = immediateSelectors.some((selector) => element.matches(selector));

      if (isImmediate) {
        requestAnimationFrame(() => element.classList.add("is-motion-visible"));
        return;
      }

      observer.observe(element);
    });
  };

  const setPressedState = (element, pressed) => {
    element.classList.toggle("is-pressed", pressed);
  };

  const bindPressFeedback = () => {
    const interactiveElements = uniqueElements(interactiveSelectors);

    interactiveElements.forEach((element) => {
      element.addEventListener("pointerdown", () => setPressedState(element, true));
      element.addEventListener("pointerup", () => setPressedState(element, false));
      element.addEventListener("pointercancel", () => setPressedState(element, false));
      element.addEventListener("pointerleave", () => setPressedState(element, false));
      element.addEventListener("blur", () => setPressedState(element, false));
    });
  };

  const bindFieldFeedback = () => {
    const fields = Array.from(document.querySelectorAll("input, select, textarea"));

    fields.forEach((field) => {
      const label = field.closest("label");

      if (!label) {
        return;
      }

      const syncValueState = () => {
        const hasValue = field.type === "checkbox" || field.type === "radio"
          ? field.checked
          : String(field.value || "").trim().length > 0;

        label.classList.toggle("has-value", hasValue);
      };

      field.addEventListener("focus", () => label.classList.add("field-is-active"));
      field.addEventListener("blur", () => label.classList.remove("field-is-active"));
      field.addEventListener("input", syncValueState);
      field.addEventListener("change", syncValueState);
      field.addEventListener("invalid", () => label.classList.add("field-has-error"));

      syncValueState();
    });
  };

  const bindChoiceFeedback = () => {
    const choices = Array.from(document.querySelectorAll(".choice-tile input"));

    choices.forEach((choice) => {
      const tile = choice.closest(".choice-tile");

      if (!tile) {
        return;
      }

      const syncChoice = () => {
        tile.classList.toggle("is-selected", choice.checked);
      };

      choice.addEventListener("change", syncChoice);
      syncChoice();
    });
  };

  const bindDetailsFeedback = () => {
    const detailsElements = Array.from(document.querySelectorAll("details"));

    detailsElements.forEach((details) => {
      details.addEventListener("toggle", () => {
        details.classList.toggle("is-open", details.open);
      });
    });
  };

  const bindFormFeedback = () => {
    const forms = Array.from(document.querySelectorAll("form"));

    forms.forEach((form) => {
      form.addEventListener("submit", () => {
        form.classList.add("is-submitting");
        form.setAttribute("aria-busy", "true");

        const submitButton = form.querySelector("button[type='submit'], input[type='submit']");

        if (submitButton) {
          submitButton.classList.add("is-submitting");
        }
      });
    });
  };

  const animateNumber = (element) => {
    if (isReduced() || element.dataset.numberAnimated === "true") {
      return;
    }

    const original = element.textContent.trim();
    const match = original.match(/^(\d+)(.*)$/);

    if (!match) {
      return;
    }

    const target = Number(match[1]);
    const suffix = match[2];
    const duration = Math.min(920, 480 + target * 4);
    const start = performance.now();

    element.dataset.numberAnimated = "true";

    const tick = (now) => {
      const elapsed = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - elapsed, 3);
      const value = Math.round(target * eased);

      element.textContent = `${value}${suffix}`;

      if (elapsed < 1) {
        requestAnimationFrame(tick);
      } else {
        element.textContent = original;
      }
    };

    requestAnimationFrame(tick);
  };

  const bindScoreAnimations = () => {
    const scores = uniqueElements(scoreSelectors);

    if (isReduced() || !("IntersectionObserver" in window)) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return;
          }

          animateNumber(entry.target);
          observer.unobserve(entry.target);
        });
      },
      {
        threshold: 0.6
      }
    );

    scores.forEach((score) => observer.observe(score));
  };

  const isNavigableLink = (link, event) => {
    if (event.defaultPrevented || event.button !== 0) {
      return false;
    }

    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return false;
    }

    if (link.target || link.download || link.hasAttribute("data-no-transition")) {
      return false;
    }

    const destination = new URL(link.href, window.location.href);

    if (destination.origin !== window.location.origin) {
      return false;
    }

    if (destination.pathname === window.location.pathname && destination.hash) {
      return false;
    }

    return true;
  };

  const bindPageTransitions = () => {
    const links = Array.from(document.querySelectorAll("a[href]"));

    links.forEach((link) => {
      link.addEventListener("click", (event) => {
        if (isReduced() || !isNavigableLink(link, event)) {
          return;
        }

        event.preventDefault();
        body.classList.add("is-page-leaving");
        body.dataset.motionStatus = "leaving";

        window.setTimeout(() => {
          window.location.assign(link.href);
        }, 140);
      });
    });
  };

  const bindScrollState = () => {
    const header = document.querySelector(".site-header");
    let latestScrollY = window.scrollY;
    let ticking = false;

    if (!header) {
      return;
    }

    const update = () => {
      const currentScrollY = window.scrollY;

      header.classList.toggle("is-scrolled", currentScrollY > 12);
      header.dataset.scrollDirection = currentScrollY > latestScrollY ? "down" : "up";
      latestScrollY = currentScrollY;
      ticking = false;
    };

    window.addEventListener(
      "scroll",
      () => {
        if (ticking) {
          return;
        }

        ticking = true;
        requestAnimationFrame(update);
      },
      {
        passive: true
      }
    );

    update();
  };

  const refreshMotionPreference = () => {
    setInteractionMode();

    if (isReduced()) {
      document.querySelectorAll("[data-motion-item]").forEach((element) => {
        element.classList.add("is-motion-visible");
      });
    }
  };

  const init = () => {
    root.classList.add("has-js");
    setViewportHeight();
    setInteractionMode();

    const motionElements = prepareMotion();

    revealMotion(motionElements);
    bindPressFeedback();
    bindFieldFeedback();
    bindChoiceFeedback();
    bindDetailsFeedback();
    bindFormFeedback();
    bindScoreAnimations();
    bindPageTransitions();
    bindScrollState();

    body.dataset.motionStatus = "ready";
    body.classList.add("is-page-ready");
  };

  window.addEventListener("resize", setViewportHeight, { passive: true });
  window.visualViewport?.addEventListener("resize", setViewportHeight, { passive: true });
  reducedMotionQuery.addEventListener?.("change", refreshMotionPreference);
  finePointerQuery.addEventListener?.("change", setInteractionMode);
  window.addEventListener("pageshow", () => body.classList.remove("is-page-leaving"));

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
