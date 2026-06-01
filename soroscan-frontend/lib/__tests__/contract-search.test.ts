import type { Contract } from "@/components/ingest/contract-types";
import {
  filterContractsByQuery,
  searchContracts,
} from "@/lib/contract-search";

const mockContracts: Contract[] = [
  {
    id: "1",
    contractId: "CCAAABBB1111111111111111111111111111111111111111111111",
    name: "Stellar Token",
    description: "Main payment token",
    tags: ["token", "payment"],
    status: "active",
    eventCount: 100,
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  },
  {
    id: "2",
    contractId: "CCDDDEEE2222222222222222222222222222222222222222222222",
    name: "Swap Pool",
    description: "DEX liquidity pool",
    tags: ["defi", "swap"],
    status: "active",
    eventCount: 50,
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  },
  {
    id: "3",
    contractId: "CCFFFAAA3333333333333333333333333333333333333333333333",
    name: "NFT Marketplace",
    description: "Collectibles trading",
    tags: ["nft"],
    status: "inactive",
    eventCount: 10,
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  },
];

describe("contract-search", () => {
  describe("searchContracts", () => {
    it("returns empty array for empty query", () => {
      expect(searchContracts("", mockContracts)).toEqual([]);
      expect(searchContracts("   ", mockContracts)).toEqual([]);
    });

    it("fuzzy matches contract name", () => {
      const results = searchContracts("stelr tokn", mockContracts);
      expect(results.length).toBeGreaterThan(0);
      expect(results[0].contract.name).toBe("Stellar Token");
    });

    it("matches partial contract ID", () => {
      const results = searchContracts("CCDDDEEE", mockContracts);
      expect(results[0].contract.name).toBe("Swap Pool");
    });

    it("matches tags", () => {
      const results = searchContracts("defi", mockContracts);
      expect(results.some((r) => r.contract.name === "Swap Pool")).toBe(true);
    });

    it("sorts results by relevance (score descending)", () => {
      const results = searchContracts("c", mockContracts);
      expect(results.length).toBeGreaterThan(1);
      for (let i = 1; i < results.length; i++) {
        expect(results[i - 1].score).toBeGreaterThanOrEqual(results[i].score);
      }
    });

    it("respects limit parameter", () => {
      const results = searchContracts("c", mockContracts, 1);
      expect(results).toHaveLength(1);
    });
  });

  describe("filterContractsByQuery", () => {
    it("returns all contracts when query is empty", () => {
      expect(filterContractsByQuery("", mockContracts)).toHaveLength(3);
      expect(filterContractsByQuery("  ", mockContracts)).toHaveLength(3);
    });

    it("filters contracts by fuzzy query", () => {
      const filtered = filterContractsByQuery("nft", mockContracts);
      expect(filtered).toHaveLength(1);
      expect(filtered[0].name).toBe("NFT Marketplace");
    });
  });
});
