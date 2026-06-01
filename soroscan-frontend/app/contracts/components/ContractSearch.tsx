"use client";

import * as React from "react";
import { Search, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/terminal/Input";
import { searchContracts } from "@/lib/contract-search";
import type { Contract } from "@/components/ingest/contract-types";

const SUGGESTION_LIMIT = 8;
const LISTBOX_ID = "contract-search-suggestions";

export interface ContractSearchProps {
  contracts: Contract[];
  value: string;
  onChange: (query: string) => void;
  onSelect?: (contract: Contract) => void;
  placeholder?: string;
  className?: string;
}

export function ContractSearch({
  contracts,
  value,
  onChange,
  onSelect,
  placeholder = "Search contracts...",
  className,
}: ContractSearchProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [activeIndex, setActiveIndex] = React.useState(-1);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const listRef = React.useRef<HTMLUListElement>(null);

  const suggestions = React.useMemo(() => {
    if (!value.trim()) {
      return [];
    }
    return searchContracts(value, contracts, SUGGESTION_LIMIT);
  }, [value, contracts]);

  const showSuggestions = isOpen && suggestions.length > 0;

  React.useEffect(() => {
    setActiveIndex(-1);
  }, [value, suggestions.length]);

  const closeSuggestions = () => {
    setIsOpen(false);
    setActiveIndex(-1);
  };

  const selectContract = (contract: Contract) => {
    onChange(contract.name);
    closeSuggestions();
    onSelect?.(contract);
    inputRef.current?.blur();
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (!showSuggestions && value.trim() && suggestions.length > 0) {
        event.preventDefault();
        setIsOpen(true);
        setActiveIndex(event.key === "ArrowDown" ? 0 : suggestions.length - 1);
        return;
      }
    }

    if (!showSuggestions) {
      return;
    }

    switch (event.key) {
      case "ArrowDown": {
        event.preventDefault();
        setActiveIndex((prev) =>
          prev < suggestions.length - 1 ? prev + 1 : 0
        );
        break;
      }
      case "ArrowUp": {
        event.preventDefault();
        setActiveIndex((prev) =>
          prev > 0 ? prev - 1 : suggestions.length - 1
        );
        break;
      }
      case "Enter": {
        if (activeIndex >= 0 && suggestions[activeIndex]) {
          event.preventDefault();
          selectContract(suggestions[activeIndex].contract);
        }
        break;
      }
      case "Escape": {
        event.preventDefault();
        closeSuggestions();
        break;
      }
      case "Tab": {
        closeSuggestions();
        break;
      }
      default:
        break;
    }
  };

  React.useEffect(() => {
    if (activeIndex < 0 || !listRef.current) {
      return;
    }
    const item = listRef.current.children[activeIndex] as HTMLElement | undefined;
    item?.scrollIntoView?.({ block: "nearest" });
  }, [activeIndex]);

  const activeOptionId =
    activeIndex >= 0 ? `${LISTBOX_ID}-option-${activeIndex}` : undefined;

  return (
    <div className={cn("relative w-full", className)}>
      <div className="relative">
        <Input
          ref={inputRef}
          hideIndicator
          type="search"
          role="combobox"
          aria-expanded={showSuggestions}
          aria-controls={LISTBOX_ID}
          aria-autocomplete="list"
          aria-activedescendant={activeOptionId}
          placeholder={placeholder}
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => {
            if (value.trim()) {
              setIsOpen(true);
            }
          }}
          onBlur={() => {
            window.setTimeout(closeSuggestions, 150);
          }}
          onKeyDown={handleKeyDown}
          className="pr-16"
        />
        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2 pointer-events-none">
          {value ? (
            <button
              type="button"
              tabIndex={-1}
              aria-label="Clear search"
              className="pointer-events-auto text-terminal-gray hover:text-terminal-green transition-colors"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                onChange("");
                closeSuggestions();
                inputRef.current?.focus();
              }}
            >
              <X className="h-4 w-4" />
            </button>
          ) : null}
          <Search className="h-4 w-4 text-terminal-gray" aria-hidden />
        </div>
      </div>

      {showSuggestions ? (
        <ul
          ref={listRef}
          id={LISTBOX_ID}
          role="listbox"
          className="absolute z-50 mt-1 w-full max-h-64 overflow-y-auto border border-terminal-green/30 bg-terminal-black shadow-glow-green/10"
        >
          {suggestions.map(({ contract }, index) => (
            <li
              key={contract.id}
              id={`${LISTBOX_ID}-option-${index}`}
              role="option"
              aria-selected={index === activeIndex}
              className={cn(
                "cursor-pointer px-4 py-3 font-terminal-mono text-sm border-b border-terminal-gray/20 last:border-b-0 transition-colors",
                index === activeIndex
                  ? "bg-terminal-green/15 text-terminal-green"
                  : "text-terminal-gray hover:bg-terminal-green/10 hover:text-terminal-green"
              )}
              onMouseDown={(e) => e.preventDefault()}
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => selectContract(contract)}
            >
              <div className="font-semibold text-terminal-green">{contract.name}</div>
              <div className="text-xs text-terminal-cyan font-mono mt-0.5 truncate">
                {contract.contractId}
              </div>
              {contract.tags && contract.tags.length > 0 ? (
                <div className="flex gap-1 flex-wrap mt-1.5">
                  {contract.tags.slice(0, 3).map((tag) => (
                    <span
                      key={tag}
                      className="text-[10px] px-1.5 py-0.5 bg-terminal-cyan/10 text-terminal-cyan border border-terminal-cyan/30"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
