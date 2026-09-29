"use client";

import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";

/** "1234567.5" -> "1,234,567.5", keeping whatever decimals were typed. */
function withCommas(raw: string): string {
  if (!raw) return "";
  const [whole, fraction] = raw.split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return fraction !== undefined ? `${grouped}.${fraction}` : grouped;
}

/** Keep digits (and one decimal point, with up to `decimals` places). */
function clean(text: string, decimals: number): string {
  const digitsAndDot = text.replace(decimals > 0 ? /[^\d.]/g : /\D/g, "");
  if (decimals === 0) return digitsAndDot.replace(/^0+(?=\d)/, "");
  const [whole, ...rest] = digitsAndDot.split(".");
  const wholePart = whole.replace(/^0+(?=\d)/, "");
  if (rest.length === 0) return wholePart;
  return `${wholePart || "0"}.${rest.join("").slice(0, decimals)}`;
}

interface NumberInputProps {
  value: string | number | null | undefined;
  /** The number as a plain string ("1234.5", no commas), or null when empty. */
  onValueChange: (value: string | null) => void;
  /** Decimal places allowed; 0 for whole numbers only. */
  decimals?: number;
  max?: number;
  placeholder?: string;
  id?: string;
}

/**
 * A money/count field that shows thousands separators as you type and only
 * ever holds a non-negative number: there is no way to type a minus sign or
 * a letter into it. A text input rather than type="number", because number
 * inputs cannot display commas and quietly accept "-5" and "1e3".
 */
export function NumberInput({
  value,
  onValueChange,
  decimals = 0,
  max,
  placeholder,
  id,
}: NumberInputProps) {
  const toText = (v: NumberInputProps["value"]) =>
    v === null || v === undefined || v === "" ? "" : clean(String(v), decimals);
  const [text, setText] = useState(() => toText(value));

  // Follow outside changes (e.g. the form loading an existing job), without
  // clobbering a half-typed "12." while the value it stands for is unchanged.
  useEffect(() => {
    if (Number(text || NaN) !== Number(toText(value) || NaN)) setText(toText(value));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return (
    <Input
      id={id}
      inputMode={decimals > 0 ? "decimal" : "numeric"}
      placeholder={placeholder}
      value={withCommas(text)}
      onChange={(e) => {
        let next = clean(e.target.value, decimals);
        if (max !== undefined && next && Number(next) > max) next = String(max);
        setText(next);
        onValueChange(next === "" || next === "." ? null : next.replace(/\.$/, ""));
      }}
    />
  );
}
