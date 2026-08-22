import { useState } from "react";

const STEP_MS = 60 * 60 * 1000;
const RATE_STEPS = [1, 2, 4, 8];

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
}

function formatDate(date) {
  return date.toLocaleDateString([], { weekday: "short", month: "short", day: "2-digit", year: "numeric" });
}

function CalendarPopover({ date, onSelectDate }) {
  const monthStart = new Date(date.getFullYear(), date.getMonth(), 1);
  const daysInMonth = new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
  const leadingDays = monthStart.getDay();
  const cells = Array.from({ length: Math.ceil((leadingDays + daysInMonth) / 7) * 7 }, (_, index) => {
    const day = index - leadingDays + 1;
    return day > 0 && day <= daysInMonth ? day : null;
  });

  return (
    <div className="calendar-popover hud-frame" role="dialog" aria-label="Simulation calendar">
      <div className="calendar-heading">
        <span className="eyebrow">Simulation date</span>
        <strong>{date.toLocaleDateString([], { month: "long", year: "numeric" })}</strong>
      </div>
      <div className="calendar-weekdays">{["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map((day) => <span key={day}>{day}</span>)}</div>
      <div className="calendar-grid">
        {cells.map((day, index) => day ? (
          <button
            type="button"
            className={day === date.getDate() ? "calendar-day current" : "calendar-day"}
            key={`${day}-${index}`}
            onClick={() => onSelectDate(new Date(date.getFullYear(), date.getMonth(), day, date.getHours(), date.getMinutes(), date.getSeconds(), date.getMilliseconds()))}
            aria-label={`Select ${date.toLocaleDateString([], { month: "long" })} ${day}`}
          >
            {day}
          </button>
        ) : <span className="calendar-day" key={`${day}-${index}`} />)}
      </div>
      <span className="eyebrow calendar-note">All object positions use this simulation time</span>
    </div>
  );
}

export default function TimeControls({ currentTime, playing, playbackRate, onTogglePlay, onSetRate, onStep, onSelectDate }) {
  const [calendarOpen, setCalendarOpen] = useState(false);
  const rateMagnitude = Math.abs(playbackRate);
  const rateLabel = `${playbackRate < 0 ? "−" : "×"}${rateMagnitude}`;

  return (
    <div className="time-controls" onMouseEnter={() => setCalendarOpen(true)} onMouseLeave={() => setCalendarOpen(false)}>
      <button type="button" className="time-jump-button" onClick={() => onStep(-STEP_MS)} aria-label="Step simulation one hour into the past" title="Step one hour backward">◀</button>
      <button type="button" className="time-rate-button" onClick={() => onSetRate(-Math.max(1, rateMagnitude * 2))} aria-label="Run simulation backward faster" title="Fast reverse">◀◀</button>
      <button type="button" className="time-play-button" onClick={onTogglePlay} aria-label={playing ? "Pause simulation" : "Play simulation"} title={playing ? "Pause" : "Play"}>{playing ? "Ⅱ" : "▶"}</button>
      <button type="button" className="time-rate-button" onClick={() => onSetRate(Math.max(1, rateMagnitude * 2))} aria-label="Run simulation forward faster" title="Fast forward">▶▶</button>
      <button type="button" className="time-jump-button" onClick={() => onStep(STEP_MS)} aria-label="Step simulation one hour into the future" title="Step one hour forward">▶</button>
      <div className="time-readout">
        <strong className="mono">{formatTime(currentTime)}</strong>
        <span className="eyebrow">{formatDate(currentTime)} // {rateLabel} SIM</span>
      </div>
      {calendarOpen && <CalendarPopover date={currentTime} onSelectDate={onSelectDate} />}
      <div className="time-rate-presets" aria-label="Playback rate presets">
        {RATE_STEPS.map((rate) => <button type="button" className={rateMagnitude === rate && playbackRate > 0 ? "rate-preset active" : "rate-preset"} key={rate} onClick={() => onSetRate(rate)}>{rate}×</button>)}
      </div>
    </div>
  );
}
