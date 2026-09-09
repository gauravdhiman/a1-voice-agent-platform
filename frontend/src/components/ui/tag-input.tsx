"use client";

import * as React from "react";
import { X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const DEFAULT_DELIMITERS = [",", " "] as const;

export interface TagInputProps
  extends Omit<
    React.ComponentPropsWithoutRef<"input">,
    "value" | "defaultValue" | "onChange"
  > {
  /** Controlled tag values displayed before the input. */
  value: string[];
  /** Called whenever a tag is added or removed. */
  onChange: (value: string[]) => void;
  /** Literal delimiters that commit the current input into a tag. */
  delimiters?: readonly string[];
  /** Optional class name applied to the tag container. */
  containerClassName?: string;
}

interface DelimitedInput {
  tags: string[];
  remainder: string;
}

function splitCompleteTags(
  inputValue: string,
  delimiters: readonly string[],
): DelimitedInput {
  const tags: string[] = [];
  let remainder = inputValue;

  while (true) {
    let delimiterIndex = -1;
    let delimiterLength = 0;

    for (const delimiter of delimiters) {
      if (!delimiter) continue;

      const index = remainder.indexOf(delimiter);
      if (
        index !== -1 &&
        (delimiterIndex === -1 ||
          index < delimiterIndex ||
          (index === delimiterIndex && delimiter.length > delimiterLength))
      ) {
        delimiterIndex = index;
        delimiterLength = delimiter.length;
      }
    }

    if (delimiterIndex === -1) break;

    const tag = remainder.slice(0, delimiterIndex).trim();
    if (tag) tags.push(tag);
    remainder = remainder.slice(delimiterIndex + delimiterLength);
  }

  return { tags, remainder };
}

/**
 * Controlled input for delimiter-separated values displayed as removable pills.
 * Delimiters are literal strings and can be customized for each use case.
 */
export const TagInput = React.forwardRef<HTMLInputElement, TagInputProps>(
  function TagInput(
    {
      className,
      containerClassName,
      delimiters = DEFAULT_DELIMITERS,
      disabled,
      onBlur,
      onKeyDown,
      onChange,
      value,
      ...inputProps
    },
    forwardedRef,
  ) {
    const [inputValue, setInputValue] = React.useState("");
    const inputRef = React.useRef<HTMLInputElement>(null);

    const setInputRef = (node: HTMLInputElement | null) => {
      inputRef.current = node;
      if (typeof forwardedRef === "function") {
        forwardedRef(node);
      } else if (forwardedRef) {
        forwardedRef.current = node;
      }
    };

    const appendTags = (pendingTags: string[]) => {
      const nextValue = [...value];
      const existingTags = new Set(value);

      for (const pendingTag of pendingTags) {
        const tag = pendingTag.trim();
        if (tag && !existingTags.has(tag)) {
          nextValue.push(tag);
          existingTags.add(tag);
        }
      }

      if (nextValue.length !== value.length) {
        onChange(nextValue);
      }
    };

    const commitInput = () => {
      appendTags([inputValue]);
      setInputValue("");
    };

    const removeTag = (indexToRemove: number) => {
      onChange(value.filter((_, index) => index !== indexToRemove));
      inputRef.current?.focus();
    };

    const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
      const { tags, remainder } = splitCompleteTags(
        event.target.value,
        delimiters,
      );
      appendTags(tags);
      setInputValue(remainder);
    };

    const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
      const isDelimiter = delimiters.some(
        (delimiter) => delimiter.length === 1 && delimiter === event.key,
      );

      if (event.key === "Enter" || isDelimiter) {
        event.preventDefault();
        commitInput();
        return;
      }

      if (event.key === "Backspace" && !inputValue && value.length > 0) {
        event.preventDefault();
        removeTag(value.length - 1);
        return;
      }

      onKeyDown?.(event);
    };

    const handleBlur = (event: React.FocusEvent<HTMLInputElement>) => {
      commitInput();
      onBlur?.(event);
    };

    return (
      <div
        className={cn(
          "flex min-h-9 w-full flex-wrap items-center gap-1.5 rounded-md border border-input bg-background px-2 py-1 shadow-xs transition-[color,box-shadow] focus-within:border-ring focus-within:ring-ring/50 focus-within:ring-[3px]",
          disabled && "cursor-not-allowed opacity-50",
          containerClassName,
        )}
        onClick={() => inputRef.current?.focus()}
        data-disabled={disabled || undefined}
      >
        {value.map((tag, index) => (
          <Badge key={`${tag}-${index}`} variant="secondary" className="gap-1 pr-1">
            <span>{tag}</span>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-4 w-4 rounded-sm p-0 text-muted-foreground hover:bg-transparent hover:text-foreground"
              aria-label={`Remove ${tag}`}
              disabled={disabled}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => removeTag(index)}
            >
              <X className="h-3 w-3" aria-hidden="true" />
            </Button>
          </Badge>
        ))}
        <Input
          {...inputProps}
          ref={setInputRef}
          type="text"
          value={inputValue}
          disabled={disabled}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          className={cn(
            "h-7 min-w-[12rem] flex-1 border-0 bg-transparent px-1 py-0 shadow-none focus-visible:border-transparent focus-visible:ring-0",
            className,
          )}
        />
      </div>
    );
  },
);

TagInput.displayName = "TagInput";
