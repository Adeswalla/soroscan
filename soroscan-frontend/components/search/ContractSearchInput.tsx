"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Contract } from "@/components/ingest/contract-types";
import { searchContracts, type ContractSearchResult } from "@/lib/contract-search";
import styles from "./ContractSearchInput.module.css";

interface ContractSearchInputProps {
  contracts: Contract[];
  onSelect: (contract: Contract) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function ContractSearchInput({
  contracts,
  onSelect,
  placeholder = "Search contracts...",
  disabled = false,
}: ContractSearchInputProps) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<ContractSearchResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const selectedItemRef = useRef<HTMLDivElement>(null);

  // Handle input change - search and show dropdown
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.currentTarget.value;
      setQuery(value);
      setSelectedIndex(-1);

      if (value.trim()) {
        const results = searchContracts(value, contracts, 8);
        setSuggestions(results);
        setIsOpen(true);
      } else {
        setSuggestions([]);
        setIsOpen(false);
      }
    },
    [contracts]
  );

  // Handle selection
  const handleSelect = useCallback(
    (contract: Contract) => {
      setQuery("");
      setSuggestions([]);
      setIsOpen(false);
      setSelectedIndex(-1);
      onSelect(contract);
    },
    [onSelect]
  );

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (!isOpen) {
        if (e.key === "ArrowDown") {
          e.preventDefault();
          setIsOpen(true);
          setSelectedIndex(0);
        }
        return;
      }

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setSelectedIndex((prev) =>
            prev < suggestions.length - 1 ? prev + 1 : prev
          );
          break;

        case "ArrowUp":
          e.preventDefault();
          setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1));
          break;

        case "Enter":
          e.preventDefault();
          if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
            handleSelect(suggestions[selectedIndex].contract);
          }
          break;

        case "Escape":
          e.preventDefault();
          setIsOpen(false);
          setSelectedIndex(-1);
          break;

        case "Tab":
          if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
            handleSelect(suggestions[selectedIndex].contract);
          }
          setIsOpen(false);
          break;

        default:
          break;
      }
    },
    [isOpen, selectedIndex, suggestions, handleSelect]
  );

  // Handle click outside to close dropdown
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setSelectedIndex(-1);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  // Scroll selected item into view
  useEffect(() => {
    selectedItemRef.current?.scrollIntoView?.({ block: "nearest" });
  }, [selectedIndex]);

  return (
    <div className={styles.container}>
      <input
        ref={inputRef}
        type="text"
        value={query}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onFocus={() => query.trim() && setIsOpen(true)}
        placeholder={placeholder}
        disabled={disabled}
        className={styles.input}
        autoComplete="off"
        aria-autocomplete="list"
        aria-expanded={isOpen}
        aria-controls="contract-suggestions"
      />

      {isOpen && suggestions.length > 0 && (
        <div
          id="contract-suggestions"
          ref={dropdownRef}
          className={styles.dropdown}
          role="listbox"
        >
          {suggestions.map((result, index) => (
            <div
              key={result.contract.id}
              ref={index === selectedIndex ? selectedItemRef : null}
              role="option"
              aria-selected={index === selectedIndex}
              className={`${styles.suggestion} ${
                index === selectedIndex ? styles.selected : ""
              }`}
              onClick={() => handleSelect(result.contract)}
              onMouseEnter={() => setSelectedIndex(index)}
            >
              <div className={styles.suggestionContent}>
                {/* Contract Name */}
                <div className={styles.suggestionName}>
                  {result.matches.name ? (
                    <div
                      dangerouslySetInnerHTML={{ __html: result.matches.name }}
                    />
                  ) : (
                    result.contract.name
                  )}
                </div>

                {/* Contract ID */}
                <div className={styles.suggestionId}>
                  {result.matches.contractId ? (
                    <div
                      dangerouslySetInnerHTML={{
                        __html: result.matches.contractId,
                      }}
                    />
                  ) : (
                    result.contract.contractId
                  )}
                </div>

                {/* Description (if available) */}
                {result.contract.description && (
                  <div className={styles.suggestionDescription}>
                    {result.matches.description ? (
                      <div
                        dangerouslySetInnerHTML={{
                          __html: result.matches.description,
                        }}
                      />
                    ) : (
                      result.contract.description.substring(0, 60)
                    )}
                  </div>
                )}

                {/* Tags */}
                {result.contract.tags && result.contract.tags.length > 0 && (
                  <div className={styles.suggestionTags}>
                    {result.contract.tags.slice(0, 2).map((tag) => (
                      <span key={tag} className={styles.tag}>
                        {tag}
                      </span>
                    ))}
                    {result.contract.tags.length > 2 && (
                      <span className={styles.tag}>
                        +{result.contract.tags.length - 2}
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Relevance indicator */}
              <div className={styles.relevance}>
                <div className={styles.relevanceBar}>
                  <div
                    className={styles.relevanceFill}
                    style={{
                      width: `${Math.min(100, (result.score / 30000) * 100)}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {isOpen && query.trim() && suggestions.length === 0 && (
        <div className={styles.noResults}>No contracts found</div>
      )}
    </div>
  );
}
