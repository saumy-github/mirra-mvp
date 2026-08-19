export type RichTextSegment = {
  text: string;
  emphasis?: boolean;
  breakAfter?: boolean;
};

export type RichText = readonly RichTextSegment[];

export type NavigationItem = {
  label: string;
  href: string;
};

export type StoryCardContent = {
  number: string;
  color: "mint" | "lime" | "blue" | "paper";
  titleLines: readonly string[];
  body: RichText;
  media?: {
    src: string;
    alt: string;
  };
};

export type FeatureCardContent = {
  number: string;
  label: string;
  titleLines: readonly string[];
  body: RichText;
  supporting?: RichText;
  media: {
    video: string;
    poster: string;
    alt: string;
  };
  featured?: boolean;
};

export type FooterLink = NavigationItem;

export type FooterLinkColumn = {
  title: string;
  links: readonly FooterLink[];
};

export const MIRRA_NAVIGATION = [
  { label: "Home", href: "/" },
  { label: "Product", href: "/#product" },
  { label: "FAQ", href: "/faq" },
  { label: "Pricing", href: "/pricing" },
] as const satisfies readonly NavigationItem[];

export const MIRRA_HEADER = {
  brand: "Mirra",
  homeLabel: "Mirra homepage",
  login: {
    label: "Login",
    ariaLabel: "Log in to Mirra",
    // Mirra's own auth route — the standalone site pointed at the ChatGPT
    // starter template's sign-in, which does not exist in this app.
    href: "/auth/login",
  },
  demo: {
    label: "Join",
    href: "/#book-a-demo",
  },
} as const;

export const MIRRA_HERO = {
  titleLines: ["Realistic Virtual Try On", "for your Shopify store"],
  accessibleTitle: "Realistic Virtual Try On for your Shopify store",
  supportLines: [
    "See exactly how Mirra fits",
    "into your Shopify store.",
  ],
} as const;

export const MIRRA_LEARN = {
  eyebrow: "What it’s all about",
  title: [
    { text: "Let customers see how your clothes fit before they buy. Eliminate " },
    { text: "sizing issues", emphasis: true },
    { text: ", cut " },
    { text: "return rates", emphasis: true },
    { text: ", and boost " },
    { text: "conversions", emphasis: true },
    { text: "." },
  ],
  body:
    "Mirra brings the fitting-room moment into your Shopify store—reducing sizing uncertainty before it becomes bracket ordering, avoidable returns, and lost margin.",
} as const satisfies {
  eyebrow: string;
  title: RichText;
  body: string;
};

export const MIRRA_TRUST = {
  peopleLabel: "Used by X+ people",
  brandsLabel: "Trusted by fashion brands",
  peopleImages: Array.from({ length: 7 }, (_, index) => `/mwg/person-${index + 1}.png`),
  brandLogos: Array.from({ length: 14 }, (_, index) => `/mwg/logo-client-${index + 1}.svg`),
  brandLogosAriaLabel: "Fashion brands using Mirra",
} as const;

export const MIRRA_COMMERCE_PRINCIPLES = [
  {
    title: "PRODUCT PAGE",
    body: "The fit decision should happen where purchase intent is highest: on the product page.",
  },
  {
    title: "ORDER CONFIDENCE",
    body: "One intentional order is better for the customer — and the margin — than two speculative sizes.",
  },
  {
    title: "REALISM",
    body: "A virtual try-on should represent the garment, not a flattering AI guess.",
  },
  {
    title: "BRAND OWNERSHIP",
    body: "The shopper should never need to leave your store, download an app, or enter a marketplace.",
  },
  {
    title: "FAST ROLLOUT",
    body: "Implementation should work with the catalogue and storefront a merchant already has.",
  },
  {
    title: "RESILIENCE",
    body: "If the try-on cannot load, the normal product page should continue without interruption.",
  },
  {
    title: "ONE EASIER DECISION",
    body: "Every layer of the experience should make one important decision easier.",
  },
] as const;

export const MIRRA_STORY_CARDS: readonly StoryCardContent[] = [
  {
    number: "1",
    color: "mint",
    titleLines: ["Fit decisions,", "earlier"],
    body: [
      {
        text: "Resolve fit uncertainty on the product page — before it becomes checkout friction, hesitation, or an abandoned cart.",
      },
    ],
  },
  {
    number: "2",
    color: "lime",
    titleLines: ["Fewer backup", "sizes"],
    body: [
      {
        text: "Reduce bracket shopping by giving customers enough fit confidence to place ",
      },
      {
        text: "one intentional order instead of two speculative ones.",
        emphasis: true,
      },
    ],
  },
  {
    number: "3",
    color: "blue",
    titleLines: ["More margin", "kept"],
    body: [
      {
        text: "Prevent avoidable returns before reverse logistics begins — protecting shipping, handling, restocking, and retained margin.",
      },
    ],
  },
  {
    number: "4",
    color: "paper",
    titleLines: ["Your store", "stays yours"],
    body: [
      { text: "Mirra lives inside your existing Shopify journey. " },
      {
        text: "No marketplace. No competitor discovery. No customer redirect.",
        emphasis: true,
      },
    ],
    media: {
      src: "/mirra/hero-editorial.webp",
      alt: "A fashion model wearing a tailored plum jacket",
    },
  },
] as const;

export const MIRRA_FEATURES: readonly FeatureCardContent[] = [
  {
    number: "01",
    label: "ONE BUTTON",
    titleLines: ["Try On. Right where it belongs."],
    body: [
      {
        text: "Mirra sits beside your existing product imagery, keeping the fit decision ",
      },
      {
        text: "inside the product page instead of outside the purchase journey.",
        emphasis: true,
      },
    ],
    media: {
      video: "/mwg/video-feature-1.mp4",
      poster: "/mwg/feature-1.png",
      alt: "A Mirra Try On button beside product imagery",
    },
  },
  {
    number: "02",
    label: "YOUR CATALOGUE",
    titleLines: ["No second catalogue to build."],
    body: [
      {
        text: "Use the product imagery you already have. Mirra turns your existing garments into try-on-ready experiences ",
      },
      {
        text: "without rebuilding your storefront around us.",
        emphasis: true,
      },
    ],
    media: {
      video: "/mwg/video-feature-2.mp4",
      poster: "/mwg/feature-2.png",
      alt: "Existing fashion catalogue becoming ready for virtual try-on",
    },
  },
  {
    number: "03",
    label: "REALISTIC TRY-ON",
    titleLines: ["Show the garment.", "Not a flattering guess."],
    body: [
      {
        text: "Mirra is built to represent how your product actually sits on the customer — so the decision is based on ",
      },
      { text: "fit, not an AI illusion.", emphasis: true },
    ],
    media: {
      video: "/mwg/video-feature-4.mp4",
      poster: "/mwg/feature-4.png",
      alt: "A realistic virtual garment try-on in motion",
    },
    featured: true,
  },
  {
    number: "04",
    label: "IN-BROWSER",
    titleLines: ["No app. No detour."],
    body: [
      {
        text: "The entire try-on happens within the shopping flow, so your customer can go from product discovery to fit evaluation ",
      },
      { text: "without leaving your store.", emphasis: true },
    ],
    media: {
      video: "/mwg/video-feature-3.mp4",
      poster: "/mwg/feature-3.png",
      alt: "An in-browser Mirra virtual try-on experience",
    },
  },
  {
    number: "05",
    label: "BRAND-OWNED",
    titleLines: ["Your customer stays yours."],
    body: [
      { text: "No marketplace.", breakAfter: true },
      { text: "No competitor recommendations.", breakAfter: true },
      { text: "No redirect into Mirra.", breakAfter: true },
      {
        text: "We improve your store. We don't replace it.",
        emphasis: true,
      },
    ],
    media: {
      video: "/mwg/video-feature-5.mp4",
      poster: "/mwg/feature-5.png",
      alt: "A brand-owned shopping journey powered by Mirra",
    },
  },
  {
    number: "06",
    label: "FAST TO SHIP",
    titleLines: ["A fitting room in 7 days."],
    body: [
      {
        text: "Mirra is designed to fit around your existing Shopify experience — so implementation doesn't become another quarter-long technology project.",
      },
    ],
    supporting: [
      {
        text: "Your storefront stays familiar. One important decision gets easier.",
        emphasis: true,
      },
    ],
    media: {
      video: "/mwg/video-feature-2.mp4",
      poster: "/mwg/feature-2.png",
      alt: "Mirra going live on a Shopify storefront in seven days",
    },
  },
] as const;

export const MIRRA_LATEST_METADATA = {
  sectionId: "mirra-in-action",
  heading: {
    primary: "What we’ve shipped,",
    secondary: "for better retail.",
  },
  brandLabel: "<Brand Name>",
  tryOnLabel: "Try it On",
} as const;

export const MIRRA_APP_CTA = {
  sectionId: "book-a-demo",
  eyebrow: "BUILT AROUND YOUR STACK",
  action: {
    label: "START A 90-DAY PILOT",
    href: "#footer",
  },
  note: "BUILT FOR SHOPIFY · NO REPLATFORMING",
  media: {
    src: "/image.png",
    alt: "Mirra appearing alongside existing Shopify stack",
  },
} as const;

export const MIRRA_FOOTER_CTA = {
  headline: "Put fit to work.",
  actions: [
    { label: "BOOK A DEMO", href: "#book-a-demo" },
    { label: "SEE MIRRA IN ACTION", href: "#mirra-in-action" },
  ],
} as const;

export const MIRRA_FOOTER_NEWSLETTER = {
  headlineLines: ["Fit is changing.", "Keep up."],
  emailLabel: "Work email",
  emailPlaceholder: "WORK EMAIL",
  submitLabel: "KEEP ME POSTED",
  body:
    "Occasional notes on virtual try-on, returns, sizing behaviour and the economics of fashion e-commerce.",
  social: {
    label: "LinkedIn",
    href: "#footer",
  },
} as const;

export const MIRRA_FOOTER_COLUMNS = [
  {
    title: "COMPANY",
    links: [
      { label: "WHY MIRRA", href: "#why-mirra" },
      { label: "OUTCOMES", href: "#outcomes" },
      { label: "CONTACT", href: "#book-a-demo" },
      { label: "CAREERS", href: "#footer" },
    ],
  },
  {
    title: "PRODUCT",
    links: [
      { label: "HOW IT WORKS", href: "#product" },
      { label: "VIRTUAL TRY-ON", href: "#mirra-in-action" },
      { label: "SHOPIFY INTEGRATION", href: "#product" },
      { label: "SECURITY", href: "#data-security" },
      { label: "FAQ", href: "/faq" },
    ],
  },
  {
    title: "FOR BRANDS",
    links: [
      { label: "BOOK A DEMO", href: "#book-a-demo" },
      { label: "SEE MIRRA IN ACTION", href: "#mirra-in-action" },
      { label: "IMPLEMENTATION", href: "#product" },
      { label: "PARTNER WITH US", href: "#book-a-demo" },
    ],
  },
] as const satisfies readonly FooterLinkColumn[];

export const MIRRA_FOOTER_LEGAL = {
  copyright: "© 2026 MIRRA",
  links: [
    { label: "TERMS", href: "#data-security" },
    { label: "PRIVACY", href: "#data-security" },
    { label: "DATA & SECURITY", href: "#data-security" },
  ],
  brand: {
    wordmark: "Mirra",
    symbolLabel: "Mirra",
  },
} as const;
