import React, { useRef } from "react";
import { motion, useScroll, useTransform } from "motion/react";
import { Linkedin } from "lucide-react";
import TextReveal from "../features/marketing/components/TextReveal";

interface TeamMember {
  name: string;
  role: string;
  details: string;
  image: string;
}

const teamMembers: TeamMember[] = [
  {
    name: "Madhavan Pankaj Srivastava",
    role: "CEO",
    details:
      "Currently in his third year at IIT BHU, Madhavan drives MIRRA's product vision and overall brand strategy.",
    image: "https://a.storyblok.com/f/283652/1260x1798/f5854e1ba5/joe-calzaghe-poster.png",
  },
  {
    name: "Saumy Bhargava",
    role: "CTO",
    details:
      "An NSUT junior architecting MIRRA's highly performant, off-thread 3D rendering pipeline.",
    image: "https://a.storyblok.com/f/283652/1414x2000/6e8a8085f4/original-sports-club-2.jpg",
  },
  {
    name: "Anant",
    role: "Founding Team",
    details:
      "Leading our store integration systems and SDK optimization while completing his third year at NSUT.",
    image: "https://a.storyblok.com/f/283652/1512x2159/196230da16/day-of-reckoning-poster.jpg",
  },
  {
    name: "Tanmay",
    role: "Founding Team",
    details:
      "Balancing his junior year at NSUT with engineering seamless, interactive PDP widgets for storefronts.",
    image: "https://a.storyblok.com/f/283652/1512x2159/778763b4ff/bruce-poster_comp.jpg",
  },
  {
    name: "Tanuj",
    role: "Founding Team",
    details:
      "A third-year NSUT student focused on scaling our secure cloud processing and backend services.",
    image:
      "https://a.storyblok.com/f/283652/1512x2159/f7f68954af/riyadh-season-football-cup-poster.jpg",
  },
];

export function ParallaxTeamCard({ member, index }: { member: TeamMember; index: number }) {
  const ref = useRef<HTMLDivElement>(null);

  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });

  // Parallax effect for the image
  const y = useTransform(scrollYProgress, [0, 1], ["-20%", "20%"]);

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 50 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-100px" }}
      transition={{ duration: 0.8, ease: [0.76, 0, 0.24, 1] }}
      className={`group relative w-full cursor-pointer ${index % 2 === 0 ? "md:pr-12 lg:pr-24" : "mt-12 md:mt-32 md:pl-12 lg:pl-24"}`}
    >
      <div className="relative aspect-3/4 overflow-hidden rounded-sm border border-line bg-bg">
        <motion.div style={{ y }} className="absolute inset-0 top-[-20%] h-[140%] w-full">
          <img
            src={member.image}
            alt={member.name}
            className="h-full w-full object-cover grayscale transition-all duration-700 ease-out group-hover:scale-105 group-hover:grayscale-0"
          />
        </motion.div>
        {/* Overlay for hover */}
        <div className="absolute inset-0 bg-bg/40 transition-colors duration-500 group-hover:bg-transparent" />
      </div>

      <div className="mt-6 flex flex-col gap-2">
        <div className="flex items-center gap-4 font-mono text-[10px] tracking-[0.2em] text-muted uppercase">
          <span>{String(index + 1).padStart(2, "0")}</span>
          <span className="h-px w-8 bg-line" />
          <TextReveal as="span" variant="chars" delay={0.08}>
            {member.role}
          </TextReveal>
        </div>

        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <TextReveal
              as="h3"
              variant="wipe-right"
              className="text-2xl font-medium tracking-tight text-ink transition-colors group-hover:text-black sm:text-3xl"
            >
              {member.name}
            </TextReveal>
            <TextReveal
              as="p"
              variant="lift"
              delay={0.16}
              className="mt-2 max-w-sm text-sm leading-relaxed text-muted"
            >
              {member.details}
            </TextReveal>
          </div>
          <a
            href="#"
            className="mt-1 flex h-10 w-10 shrink-0 transform items-center justify-center rounded-full border border-silver bg-bg text-ink shadow-xs transition-all group-hover:scale-110 hover:bg-black hover:text-white"
            onClick={(e) => e.stopPropagation()}
          >
            <Linkedin size={16} />
          </a>
        </div>
      </div>
    </motion.div>
  );
}

export default function MeetTheTeam() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="w-full pt-32 pb-0"
    >
      <div className="mx-auto max-w-260 px-5 sm:px-8">
        {/* Hero */}
        <div className="mb-24 flex flex-col items-center text-center">
          <TextReveal
            as="h1"
            variant="wipe-right"
            className="mb-6 text-5xl font-semibold tracking-tight text-ink md:text-6xl lg:text-7xl"
          >
            {"The People\nBehind Mirra"}
          </TextReveal>
          <TextReveal
            as="p"
            variant="lift"
            delay={0.24}
            className="mb-10 max-w-2xl text-lg text-muted md:text-xl"
          >
            A small team with a big obsession: rebuilding the way fashion is experienced online
          </TextReveal>
        </div>

        {/* Meet the Team */}
        <div className="mb-32" id="team">
          <div className="grid grid-cols-1 gap-12 md:grid-cols-2 md:gap-y-32">
            {teamMembers.map((member, index) => (
              <ParallaxTeamCard key={member.name} member={member} index={index} />
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
