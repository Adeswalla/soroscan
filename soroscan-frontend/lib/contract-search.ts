import fuzzysort from "fuzzysort";
import type { Contract } from "@/components/ingest/contract-types";

export interface ContractSearchResult {
  contract: Contract;
  score: number;
  matches: {
    name?: string;
    contractId?: string;
    description?: string;
  };
}

/**
 * Highlight matched portions of text with <mark> tags
 */
function highlightMatch(
  text: string,
  indices: ReadonlySet<number>
): string {
  if (indices.size === 0) {
    return text;
  }

  let result = "";
  let inTag = false;

  for (let i = 0; i < text.length; i++) {
    if (indices.has(i)) {
      if (!inTag) {
        result += "<mark>";
        inTag = true;
      }
      result += text[i];
    } else {
      if (inTag) {
        result += "</mark>";
        inTag = false;
      }
      result += text[i];
    }
  }

  if (inTag) {
    result += "</mark>";
  }

  return result;
}

/**
 * Fuzzy-search contracts by name, contract ID, description, and tags.
 * Results are sorted by relevance (best match first).
 * Returns match highlights for displaying in autocomplete.
 */
export function searchContracts(
  query: string,
  contracts: Contract[],
  limit = 10
): ContractSearchResult[] {
  const trimmed = query.trim();
  if (!trimmed) {
    return [];
  }

  const results: ContractSearchResult[] = [];

  for (const contract of contracts) {
    // Search across multiple fields
    const nameMatch = fuzzysort.single(trimmed, contract.name);
    const contractIdMatch = fuzzysort.single(trimmed, contract.contractId);
    const descriptionMatch = contract.description
      ? fuzzysort.single(trimmed, contract.description)
      : null;
    const tagsMatch = contract.tags?.length
      ? fuzzysort.single(trimmed, contract.tags.join(" "))
      : null;

    // Calculate combined score (prioritize name matches)
    const scores = [
      nameMatch ? (nameMatch.score + 10000) * 2 : 0, // Name matches weighted 2x
      contractIdMatch ? contractIdMatch.score + 10000 : 0,
      descriptionMatch ? descriptionMatch.score + 5000 : 0, // Description weighted 0.5x
      tagsMatch ? tagsMatch.score + 3000 : 0, // Tags weighted 0.3x
    ];
    const maxScore = Math.max(...scores);

    // Only include if at least one field matches
    if (maxScore > 0) {
      results.push({
        contract,
        score: maxScore,
        matches: {
          name: nameMatch ? highlightMatch(contract.name, new Set(nameMatch.indexes)) : undefined,
          contractId: contractIdMatch
            ? highlightMatch(contract.contractId, new Set(contractIdMatch.indexes))
            : undefined,
          description: descriptionMatch
            ? highlightMatch(contract.description, new Set(descriptionMatch.indexes))
            : undefined,
        },
      });
    }
  }

  // Sort by score descending (highest relevance first)
  results.sort((a, b) => b.score - a.score);

  return results.slice(0, limit);
}

/**
 * Filter contracts by query; returns all contracts when query is empty.
 */
export function filterContractsByQuery(query: string, contracts: Contract[]): Contract[] {
  const trimmed = query.trim();
  if (!trimmed) {
    return contracts;
  }

  return searchContracts(trimmed, contracts, contracts.length).map((r) => r.contract);
}
