import { describe, it, expect, beforeEach } from "@jest/globals";
import { searchContracts, filterContractsByQuery } from "@/lib/contract-search";
import type { Contract } from "@/components/ingest/contract-types";

const mockContracts: Contract[] = [
  {
    id: "1",
    contractId: "CAAA",
    name: "Payment Processor",
    description: "Handles payment processing",
    tags: ["payment", "finance"],
    status: "active",
    eventCount: 100,
    createdAt: "2024-01-01",
    updatedAt: "2024-01-15",
  },
  {
    id: "2",
    contractId: "CBBB",
    name: "Token Swap",
    description: "Automated token swapping",
    tags: ["swap", "trading"],
    status: "active",
    eventCount: 250,
    createdAt: "2024-01-02",
    updatedAt: "2024-01-16",
  },
  {
    id: "3",
    contractId: "CCCC",
    name: "Lending Protocol",
    description: "Decentralized lending platform",
    tags: ["lending", "finance"],
    status: "active",
    eventCount: 500,
    createdAt: "2024-01-03",
    updatedAt: "2024-01-17",
  },
  {
    id: "4",
    contractId: "CDDD",
    name: "Staking Manager",
    description: "Manages staking operations",
    tags: ["staking"],
    status: "active",
    eventCount: 150,
    createdAt: "2024-01-04",
    updatedAt: "2024-01-18",
  },
];

describe("contract-search", () => {
  describe("searchContracts", () => {
    it("returns empty array when query is empty", () => {
      const results = searchContracts("", mockContracts);
      expect(results).toEqual([]);
    });

    it("returns empty array when query is whitespace only", () => {
      const results = searchContracts("   ", mockContracts);
      expect(results).toEqual([]);
    });

    it("finds contracts by name match", () => {
      const results = searchContracts("payment", mockContracts);
      expect(results.length).toBeGreaterThan(0);
      expect(results[0].contract.name).toBe("Payment Processor");
    });

    it("finds contracts by contract ID match", () => {
      const results = searchContracts("CBBB", mockContracts);
      expect(results.length).toBeGreaterThan(0);
      expect(results[0].contract.contractId).toBe("CBBB");
    });

    it("finds contracts by description match", () => {
      const results = searchContracts("lending", mockContracts);
      expect(results.length).toBeGreaterThan(0);
      expect(results[0].contract.name).toContain("Lending");
    });

    it("finds contracts by tag match", () => {
      const results = searchContracts("finance", mockContracts);
      expect(results.length).toBeGreaterThan(0);
      // Should match both Payment Processor and Lending Protocol
      const names = results.map((r) => r.contract.name);
      expect(names).toContain("Payment Processor");
      expect(names).toContain("Lending Protocol");
    });

    it("performs fuzzy matching", () => {
      // "pmt" should match "payment"
      const results = searchContracts("pmt", mockContracts);
      expect(results.length).toBeGreaterThan(0);
    });

    it("sorts results by relevance (exact name match first)", () => {
      const results = searchContracts("token", mockContracts);
      // "Token Swap" should be first as it has exact match in name
      expect(results[0].contract.name).toBe("Token Swap");
    });

    it("prioritizes name matches over other fields", () => {
      // Both "Payment Processor" (name) and contracts with "payment" in description
      const results = searchContracts("payment", mockContracts);
      expect(results[0].contract.name).toBe("Payment Processor");
    });

    it("includes match highlights in results", () => {
      const results = searchContracts("payment", mockContracts);
      expect(results.length).toBeGreaterThan(0);
      // Should have highlights with <mark> tags
      const firstResult = results[0];
      expect(firstResult.matches).toBeDefined();
      if (firstResult.matches.name) {
        expect(firstResult.matches.name).toContain("<mark>");
      }
    });

    it("respects limit parameter", () => {
      const results = searchContracts("", mockContracts, 2);
      expect(results).toEqual([]);

      // Create results with all matching
      const allMatches = searchContracts("a", mockContracts, 2);
      expect(allMatches.length).toBeLessThanOrEqual(2);
    });

    it("returns results up to limit when more matches exist", () => {
      // Search for common term that matches multiple contracts
      const results = searchContracts("protocol", mockContracts, 5);
      expect(results.length).toBeLessThanOrEqual(5);
    });

    it("assigns scores to results", () => {
      const results = searchContracts("payment", mockContracts);
      expect(results.length).toBeGreaterThan(0);
      for (const result of results) {
        expect(result.score).toBeGreaterThan(0);
      }
    });

    it("handles special characters in query", () => {
      const results = searchContracts("c???", mockContracts);
      // Should not crash, may return empty or fuzzy matches
      expect(Array.isArray(results)).toBe(true);
    });

    it("handles contracts without description", () => {
      const contractsNoDesc = [
        ...mockContracts,
        {
          id: "5",
          contractId: "CEEE",
          name: "No Description Contract",
          contractId: "CEEE",
          tags: ["test"],
          status: "active" as const,
          eventCount: 10,
          createdAt: "2024-01-05",
          updatedAt: "2024-01-19",
        },
      ];
      const results = searchContracts("description", contractsNoDesc);
      expect(Array.isArray(results)).toBe(true);
      // Should not crash, even though one contract has no description
    });

    it("handles contracts without tags", () => {
      const contractsNoTags = [
        ...mockContracts,
        {
          id: "6",
          contractId: "CFFF",
          name: "No Tags Contract",
          description: "A contract without tags",
          tags: [],
          status: "active" as const,
          eventCount: 20,
          createdAt: "2024-01-06",
          updatedAt: "2024-01-20",
        },
      ];
      const results = searchContracts("contract", contractsNoTags);
      expect(results.length).toBeGreaterThan(0);
    });

    it("is case-insensitive", () => {
      const lowerResults = searchContracts("payment", mockContracts);
      const upperResults = searchContracts("PAYMENT", mockContracts);
      const mixedResults = searchContracts("PayMent", mockContracts);

      expect(lowerResults.length).toBeGreaterThan(0);
      expect(upperResults.length).toBeGreaterThan(0);
      expect(mixedResults.length).toBeGreaterThan(0);
    });
  });

  describe("filterContractsByQuery", () => {
    it("returns all contracts when query is empty", () => {
      const results = filterContractsByQuery("", mockContracts);
      expect(results).toEqual(mockContracts);
    });

    it("returns all contracts when query is whitespace only", () => {
      const results = filterContractsByQuery("   ", mockContracts);
      expect(results).toEqual(mockContracts);
    });

    it("filters contracts by query", () => {
      const results = filterContractsByQuery("payment", mockContracts);
      expect(results.length).toBeGreaterThan(0);
      expect(results.length).toBeLessThanOrEqual(mockContracts.length);
    });

    it("returns empty array when no matches found", () => {
      const results = filterContractsByQuery("xyzabc123notfound", mockContracts);
      expect(results).toEqual([]);
    });

    it("returns Contract objects not search results", () => {
      const results = filterContractsByQuery("payment", mockContracts);
      expect(results.length).toBeGreaterThan(0);
      for (const contract of results) {
        expect(contract).toHaveProperty("id");
        expect(contract).toHaveProperty("contractId");
        expect(contract).toHaveProperty("name");
        expect(contract).not.toHaveProperty("score");
        expect(contract).not.toHaveProperty("matches");
      }
    });

    it("uses fuzzy search like searchContracts", () => {
      const results = filterContractsByQuery("tkn", mockContracts); // fuzzy match for "token"
      expect(results.length).toBeGreaterThan(0);
    });
  });
});
