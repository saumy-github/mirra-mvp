import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { motion, type PanInfo } from "motion/react";
import { useReducedMotion } from "@/hooks/use-reduced-motion";

export type PinchSlot = -1 | 0 | 1;

export type PinchRenderState = {
  active: boolean;
  slot: PinchSlot;
};

type PinchCarouselProps<T> = {
  items: readonly T[];
  getKey: (item: T) => React.Key;
  getLabel: (item: T) => string;
  axis: "x" | "y";
  activeKey?: React.Key;
  onActiveChange?: (item: T, key: React.Key, index: number) => void;
  renderItem: (item: T, state: PinchRenderState) => ReactNode;
  ariaLabel: string;
  className?: string;
  viewportClassName?: string;
  stride?: number;
  debounceMs?: number;
};

type VisibleSlot<T> = {
  item: T;
  index: number;
  slot: PinchSlot;
};

const SNAP_SPRING = {
  type: "spring" as const,
  stiffness: 430,
  damping: 38,
  mass: 0.82,
};

const RETURN_SPRING = {
  bounceStiffness: 430,
  bounceDamping: 38,
  power: 0.18,
  timeConstant: 170,
};

const WHEEL_THRESHOLD = 12;
const DRAG_THRESHOLD_RATIO = 0.22;
const PROJECT_DECELERATION = 0.998;

function cx(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(" ");
}

function wrap(index: number, length: number) {
  return ((index % length) + length) % length;
}

function projectVelocity(velocity: number) {
  return (velocity / 1000) * (PROJECT_DECELERATION / (1 - PROJECT_DECELERATION));
}

function getVisibleSlots<T>(items: readonly T[], activeIndex: number): VisibleSlot<T>[] {
  const length = items.length;
  if (length === 0) return [];

  const active = items[activeIndex];
  if (active === undefined) return [];

  if (length === 1) {
    return [{ item: active, index: activeIndex, slot: 0 }];
  }

  if (length === 2) {
    const otherIndex = activeIndex === 0 ? 1 : 0;
    const other = items[otherIndex];
    if (other === undefined) {
      return [{ item: active, index: activeIndex, slot: 0 }];
    }

    return activeIndex === 0
      ? [
          { item: active, index: activeIndex, slot: 0 },
          { item: other, index: otherIndex, slot: 1 },
        ]
      : [
          { item: other, index: otherIndex, slot: -1 },
          { item: active, index: activeIndex, slot: 0 },
        ];
  }

  const previousIndex = wrap(activeIndex - 1, length);
  const nextIndex = wrap(activeIndex + 1, length);
  const previous = items[previousIndex];
  const next = items[nextIndex];

  if (previous === undefined || next === undefined) {
    return [{ item: active, index: activeIndex, slot: 0 }];
  }

  return [
    { item: previous, index: previousIndex, slot: -1 },
    { item: active, index: activeIndex, slot: 0 },
    { item: next, index: nextIndex, slot: 1 },
  ];
}

function Arrow({ axis, direction }: { axis: "x" | "y"; direction: -1 | 1 }) {
  const rotation = axis === "y" ? (direction === -1 ? -90 : 90) : direction === -1 ? 180 : 0;

  return (
    <svg
      aria-hidden
      viewBox="0 0 24 24"
      className="size-4"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ transform: `rotate(${rotation}deg)` }}
    >
      <path d="m9 5 7 7-7 7" />
    </svg>
  );
}

/**
 * A three-slot, gesture-driven garment carousel. Only the active item and its
 * immediate neighbours are mounted; longer collections wrap continuously.
 */
export function PinchCarousel<T>({
  items,
  getKey,
  getLabel,
  axis,
  activeKey,
  onActiveChange,
  renderItem,
  ariaLabel,
  className,
  viewportClassName,
  stride,
  debounceMs = 280,
}: PinchCarouselProps<T>) {
  const reduceMotion = useReducedMotion();
  const resolvedStride = Math.max(1, stride ?? (axis === "y" ? 152 : 132));
  const isControlled = activeKey !== undefined;
  const [internalKey, setInternalKey] = useState<React.Key | undefined>(() => {
    if (activeKey !== undefined) return activeKey;
    const first = items[0];
    return first === undefined ? undefined : getKey(first);
  });
  const wheelAccumulatorRef = useRef(0);
  const lastWheelStepRef = useRef(-Infinity);
  const wheelResetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const suppressClickRef = useRef(false);
  const viewportRef = useRef<HTMLDivElement>(null);

  const selectedKey = isControlled ? activeKey : internalKey;
  const matchedIndex = items.findIndex((item) => Object.is(getKey(item), selectedKey));
  const activeIndex = matchedIndex >= 0 ? matchedIndex : 0;
  const activeItem = items[activeIndex];
  const visibleSlots = useMemo(() => getVisibleSlots(items, activeIndex), [activeIndex, items]);

  const selectIndex = useCallback(
    (requestedIndex: number) => {
      const length = items.length;
      if (length < 2) return;

      const nextIndex =
        length >= 3
          ? wrap(requestedIndex, length)
          : Math.min(length - 1, Math.max(0, requestedIndex));
      const nextItem = items[nextIndex];
      if (nextItem === undefined || nextIndex === activeIndex) return;

      const nextKey = getKey(nextItem);
      if (!isControlled) setInternalKey(nextKey);
      onActiveChange?.(nextItem, nextKey, nextIndex);
    },
    [activeIndex, getKey, isControlled, items, onActiveChange],
  );

  const selectRelative = useCallback(
    (direction: -1 | 1) => {
      const length = items.length;
      if (length < 2) return;

      if (length === 2) {
        selectIndex(activeIndex === 0 ? 1 : 0);
        return;
      }

      selectIndex(activeIndex + direction);
    },
    [activeIndex, items.length, selectIndex],
  );

  const handleWheel = useCallback(
    (event: globalThis.WheelEvent) => {
      if (items.length < 2 || event.ctrlKey) return;

      // A horizontal Studio rail must never swallow the vertical gesture used
      // to move through the mobile page.
      if (axis === "x" && Math.abs(event.deltaY) > Math.abs(event.deltaX)) return;

      const rawDelta = axis === "x" ? event.deltaX : event.deltaY;
      if (rawDelta === 0) return;

      event.preventDefault();
      const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? resolvedStride : 1;
      const delta = rawDelta * unit;
      wheelAccumulatorRef.current += delta;

      if (wheelResetTimerRef.current !== null) {
        clearTimeout(wheelResetTimerRef.current);
      }
      wheelResetTimerRef.current = setTimeout(
        () => {
          wheelAccumulatorRef.current = 0;
        },
        Math.max(80, debounceMs),
      );

      const now = performance.now();
      if (
        Math.abs(wheelAccumulatorRef.current) < WHEEL_THRESHOLD ||
        now - lastWheelStepRef.current < debounceMs
      ) {
        return;
      }

      const direction = wheelAccumulatorRef.current > 0 ? 1 : -1;
      wheelAccumulatorRef.current = 0;
      lastWheelStepRef.current = now;
      selectRelative(direction);
    },
    [axis, debounceMs, items.length, resolvedStride, selectRelative],
  );

  const handleDragEnd = useCallback(
    (_event: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
      const offset = axis === "x" ? info.offset.x : info.offset.y;
      const velocity = axis === "x" ? info.velocity.x : info.velocity.y;
      const projectedOffset = offset + projectVelocity(velocity);
      const threshold = Math.max(24, Math.min(54, resolvedStride * DRAG_THRESHOLD_RATIO));

      suppressClickRef.current = Math.abs(offset) > 6;
      if (suppressClickRef.current) {
        setTimeout(() => {
          suppressClickRef.current = false;
        }, 0);
      }

      if (Math.abs(projectedOffset) >= threshold) {
        selectRelative(projectedOffset < 0 ? 1 : -1);
      }
    },
    [axis, resolvedStride, selectRelative],
  );

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLElement>) => {
      const target = event.target as HTMLElement;
      if (
        target !== event.currentTarget &&
        (target.isContentEditable || target.matches("input, textarea, select, [role='textbox']"))
      ) {
        return;
      }

      const previousKey = axis === "x" ? "ArrowLeft" : "ArrowUp";
      const nextKey = axis === "x" ? "ArrowRight" : "ArrowDown";

      if (event.key === previousKey) {
        event.preventDefault();
        selectRelative(-1);
      } else if (event.key === nextKey) {
        event.preventDefault();
        selectRelative(1);
      } else if (event.key === "Home") {
        event.preventDefault();
        selectIndex(0);
      } else if (event.key === "End") {
        event.preventDefault();
        selectIndex(items.length - 1);
      }
    },
    [axis, items.length, selectIndex, selectRelative],
  );

  useEffect(
    () => () => {
      if (wheelResetTimerRef.current !== null) {
        clearTimeout(wheelResetTimerRef.current);
      }
    },
    [],
  );

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;

    viewport.addEventListener("wheel", handleWheel, { passive: false });
    return () => viewport.removeEventListener("wheel", handleWheel);
  }, [handleWheel]);

  const liveLabel =
    activeItem === undefined
      ? "No garments"
      : `${activeIndex + 1} of ${items.length}: ${getLabel(activeItem)}`;
  const viewportStyle = { touchAction: axis === "x" ? "pan-y" : "pan-x" } as const;
  const transition = reduceMotion
    ? { duration: 0.12, ease: "linear" as const }
    : {
        x: SNAP_SPRING,
        y: SNAP_SPRING,
        opacity: { duration: 0.2, ease: [0.2, 0.8, 0.2, 1] as const },
      };

  return (
    <section
      role="region"
      aria-roledescription="carousel"
      aria-label={ariaLabel}
      aria-keyshortcuts={
        axis === "x" ? "ArrowLeft ArrowRight Home End" : "ArrowUp ArrowDown Home End"
      }
      tabIndex={0}
      onKeyDown={handleKeyDown}
      className={cx("relative isolate min-h-0 min-w-0", className)}
    >
      <div
        ref={viewportRef}
        style={viewportStyle}
        className={cx(
          "relative h-full min-h-0 w-full min-w-0 overflow-hidden bg-paper/18",
          viewportClassName,
        )}
      >
        <motion.div
          drag={items.length > 1 && !reduceMotion ? axis : false}
          dragConstraints={{ top: 0, right: 0, bottom: 0, left: 0 }}
          dragElastic={1}
          dragMomentum={false}
          dragTransition={RETURN_SPRING}
          onDragEnd={handleDragEnd}
          className={cx(
            "absolute inset-0 select-none",
            items.length > 1 && !reduceMotion && "cursor-grab",
          )}
        >
          {visibleSlots.map(({ item, index, slot }) => {
            const active = slot === 0;
            const offset = slot * resolvedStride;
            const itemKey = getKey(item);

            return (
              <div
                key={itemKey}
                className="pointer-events-none absolute inset-0 flex items-center justify-center"
                style={{ zIndex: active ? 3 : 1 }}
              >
                <motion.div
                  role="group"
                  aria-roledescription="slide"
                  aria-label={`${index + 1} of ${items.length}: ${getLabel(item)}`}
                  aria-current={active ? "true" : undefined}
                  data-active={active ? "true" : "false"}
                  data-slot={slot}
                  onClickCapture={(event) => {
                    if (suppressClickRef.current) {
                      event.preventDefault();
                      event.stopPropagation();
                      return;
                    }
                    if (active) return;
                    event.preventDefault();
                    event.stopPropagation();
                    selectIndex(index);
                  }}
                  initial={
                    reduceMotion
                      ? false
                      : {
                          opacity: 0,
                          x: axis === "x" ? offset * 1.08 : 0,
                          y: axis === "y" ? offset * 1.08 : 0,
                        }
                  }
                  animate={{
                    x: axis === "x" ? offset : 0,
                    y: axis === "y" ? offset : 0,
                    opacity: 1,
                  }}
                  transition={transition}
                  className={cx(
                    "pointer-events-auto relative shrink-0 transform-gpu",
                    !active && "cursor-pointer",
                  )}
                >
                  {renderItem(item, { active, slot })}
                </motion.div>
              </div>
            );
          })}
        </motion.div>

        {items.length > 1 && (
          <>
            <motion.button
              type="button"
              aria-label={`Previous ${ariaLabel} item`}
              onClick={() => selectRelative(-1)}
              whileTap={reduceMotion ? undefined : { scale: 0.94 }}
              transition={SNAP_SPRING}
              className={cx(
                "group/previous absolute z-20 flex items-center justify-center border-0 bg-transparent text-ink-soft",
                axis === "y" ? "inset-x-0 top-0 h-[24%]" : "inset-y-0 left-0 w-[24%]",
              )}
            >
              <span className="flex size-9 items-center justify-center rounded-full border border-line bg-paper transition-transform duration-200 motion-reduce:transition-none">
                <Arrow axis={axis} direction={-1} />
              </span>
            </motion.button>

            <motion.button
              type="button"
              aria-label={`Next ${ariaLabel} item`}
              onClick={() => selectRelative(1)}
              whileTap={reduceMotion ? undefined : { scale: 0.94 }}
              transition={SNAP_SPRING}
              className={cx(
                "group/next absolute z-20 flex items-center justify-center border-0 bg-transparent text-ink-soft",
                axis === "y" ? "inset-x-0 bottom-0 h-[24%]" : "inset-y-0 right-0 w-[24%]",
              )}
            >
              <span className="flex size-9 items-center justify-center rounded-full border border-line bg-paper transition-transform duration-200 motion-reduce:transition-none">
                <Arrow axis={axis} direction={1} />
              </span>
            </motion.button>
          </>
        )}
      </div>

      <p aria-live="polite" aria-atomic="true" className="sr-only">
        {liveLabel}
      </p>
    </section>
  );
}
