import React from "react";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ContractSearchInput } from "@/components/search/ContractSearchInput";
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
];

describe("ContractSearchInput", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("renders input field", () => {
    const onSelect = jest.fn();
    render(
      <ContractSearchInput contracts={mockContracts} onSelect={onSelect} />
    );

    const input = screen.getByPlaceholderText("Search contracts...");
    expect(input).toBeInTheDocument();
  });

  it("uses custom placeholder", () => {
    const onSelect = jest.fn();
    render(
      <ContractSearchInput
        contracts={mockContracts}
        onSelect={onSelect}
        placeholder="Find a contract..."
      />
    );

    const input = screen.getByPlaceholderText("Find a contract...");
    expect(input).toBeInTheDocument();
  });

  it("shows suggestions when typing", async () => {
    const onSelect = jest.fn();
    const user = userEvent.setup({ delay: null });
    render(
      <ContractSearchInput contracts={mockContracts} onSelect={onSelect} />
    );

    const input = screen.getByPlaceholderText("Search contracts...");
    await user.type(input, "payment");

    jest.runAllTimers();

    // Should show dropdown with suggestions
    await waitFor(() => {
      const dropdown = screen.getByRole("listbox");
      expect(dropdown).toBeInTheDocument();
      const options = screen.getAllByRole("option");
      expect(options.length).toBeGreaterThan(0);
    });
  });

  it("shows 'No contracts found' when no matches", async () => {
    const onSelect = jest.fn();
    const user = userEvent.setup({ delay: null });
    render(
      <ContractSearchInput contracts={mockContracts} onSelect={onSelect} />
    );

    const input = screen.getByPlaceholderText("Search contracts...");
    await user.type(input, "xyzabc123notfound");

    jest.runAllTimers();

    await waitFor(() => {
      expect(screen.getByText("No contracts found")).toBeInTheDocument();
    });
  });

  it("closes dropdown when clicking outside", async () => {
    const onSelect = jest.fn();
    const user = userEvent.setup({ delay: null });
    const { container } = render(
      <ContractSearchInput contracts={mockContracts} onSelect={onSelect} />
    );

    const input = screen.getByPlaceholderText("Search contracts...");
    await user.type(input, "payment");

    jest.runAllTimers();

    await waitFor(() => {
      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    // Click outside
    fireEvent.mouseDown(container);

    await waitFor(() => {
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });
  });

  it("calls onSelect with contract when clicking suggestion", async () => {
    const onSelect = jest.fn();
    const user = userEvent.setup({ delay: null });
    render(
      <ContractSearchInput contracts={mockContracts} onSelect={onSelect} />
    );

    const input = screen.getByPlaceholderText("Search contracts...");
    await user.type(input, "payment");

    jest.runAllTimers();

    await waitFor(() => {
      const options = screen.getAllByRole("option");
      expect(options.length).toBeGreaterThan(0);
    });

    const firstOption = screen.getAllByRole("option")[0];
    fireEvent.click(firstOption);

    expect(onSelect).toHaveBeenCalled();
  });

  it("clears input after selection", async () => {
    const onSelect = jest.fn();
    const user = userEvent.setup({ delay: null });
    render(
      <ContractSearchInput contracts={mockContracts} onSelect={onSelect} />
    );

    const input = screen.getByPlaceholderText(
      "Search contracts..."
    ) as HTMLInputElement;
    await user.type(input, "payment");

    jest.runAllTimers();

    await waitFor(() => {
      const options = screen.getAllByRole("option");
      expect(options.length).toBeGreaterThan(0);
    });

    const firstOption = screen.getAllByRole("option")[0];
    fireEvent.click(firstOption);

    expect(input.value).toBe("");
  });

  it("navigates suggestions with arrow keys", async () => {
    const onSelect = jest.fn();
    const user = userEvent.setup({ delay: null });
    render(
      <ContractSearchInput contracts={mockContracts} onSelect={onSelect} />
    );

    const input = screen.getByPlaceholderText("Search contracts...");
    await user.type(input, "a");

    jest.runAllTimers();

    await waitFor(() => {
      const suggestions = screen.getAllByRole("option");
      expect(suggestions.length).toBeGreaterThan(0);
    });

    // Navigate down
    fireEvent.keyDown(input, { key: "ArrowDown" });

    jest.runAllTimers();

    await waitFor(() => {
      const selected = screen.getByRole("option", { selected: true });
      expect(selected).toHaveClass("selected");
    });
  });

  it("selects with Enter key", async () => {
    const onSelect = jest.fn();
    const user = userEvent.setup({ delay: null });
    render(
      <ContractSearchInput contracts={mockContracts} onSelect={onSelect} />
    );

    const input = screen.getByPlaceholderText("Search contracts...");
    await user.type(input, "token");

    jest.runAllTimers();

    await waitFor(() => {
      const options = screen.getAllByRole("option");
      expect(options.length).toBeGreaterThan(0);
    });

    fireEvent.keyDown(input, { key: "ArrowDown" });

    jest.runAllTimers();

    await waitFor(() => {
      expect(screen.getByRole("option", { selected: true })).toBeInTheDocument();
    });

    fireEvent.keyDown(input, { key: "Enter" });

    jest.runAllTimers();

    expect(onSelect).toHaveBeenCalled();
  });

  it("closes dropdown with Escape key", async () => {
    const onSelect = jest.fn();
    const user = userEvent.setup({ delay: null });
    render(
      <ContractSearchInput contracts={mockContracts} onSelect={onSelect} />
    );

    const input = screen.getByPlaceholderText("Search contracts...");
    await user.type(input, "payment");

    jest.runAllTimers();

    await waitFor(() => {
      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    fireEvent.keyDown(input, { key: "Escape" });

    jest.runAllTimers();

    await waitFor(() => {
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });
  });

  it("respects disabled prop", () => {
    const onSelect = jest.fn();
    render(
      <ContractSearchInput
        contracts={mockContracts}
        onSelect={onSelect}
        disabled={true}
      />
    );

    const input = screen.getByPlaceholderText(
      "Search contracts..."
    ) as HTMLInputElement;
    expect(input.disabled).toBe(true);
  });

  it("displays contract details in suggestions", async () => {
    const onSelect = jest.fn();
    const user = userEvent.setup({ delay: null });
    render(
      <ContractSearchInput contracts={mockContracts} onSelect={onSelect} />
    );

    const input = screen.getByPlaceholderText("Search contracts...");
    await user.type(input, "lending");

    jest.runAllTimers();

    await waitFor(() => {
      // Check that contract ID is displayed
      const options = screen.getAllByRole("option");
      expect(options.length).toBeGreaterThan(0);
      // At least one option should contain the contract ID
      const hasContractId = options.some((option) =>
        option.textContent?.includes("CCCC")
      );
      expect(hasContractId).toBe(true);
    });
  });

  it("fuzzy matches contract names", async () => {
    const onSelect = jest.fn();
    const user = userEvent.setup({ delay: null });
    render(
      <ContractSearchInput contracts={mockContracts} onSelect={onSelect} />
    );

    const input = screen.getByPlaceholderText("Search contracts...");
    // "pmt" should fuzzy match "payment"
    await user.type(input, "pmt");

    jest.runAllTimers();

    await waitFor(() => {
      const suggestions = screen.getAllByRole("option");
      expect(suggestions.length).toBeGreaterThan(0);
    });
  });

  it("handles Tab key to select", async () => {
    const onSelect = jest.fn();
    const user = userEvent.setup({ delay: null });
    render(
      <ContractSearchInput contracts={mockContracts} onSelect={onSelect} />
    );

    const input = screen.getByPlaceholderText("Search contracts...");
    await user.type(input, "token");

    jest.runAllTimers();

    await waitFor(() => {
      const options = screen.getAllByRole("option");
      expect(options.length).toBeGreaterThan(0);
    });

    fireEvent.keyDown(input, { key: "ArrowDown" });

    jest.runAllTimers();

    await waitFor(() => {
      expect(screen.getByRole("option", { selected: true })).toBeInTheDocument();
    });

    fireEvent.keyDown(input, { key: "Tab" });

    jest.runAllTimers();

    expect(onSelect).toHaveBeenCalled();
  });
});
