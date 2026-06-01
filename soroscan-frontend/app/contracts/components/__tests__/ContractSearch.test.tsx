import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ContractSearch } from "../ContractSearch";
import type { Contract } from "@/components/ingest/contract-types";

const mockContracts: Contract[] = [
  {
    id: "1",
    contractId: "CCAAABBB1111111111111111111111111111111111111111111111",
    name: "Stellar Token",
    tags: ["token"],
    status: "active",
    eventCount: 100,
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  },
  {
    id: "2",
    contractId: "CCDDDEEE2222222222222222222222222222222222222222222222",
    name: "Swap Pool",
    tags: ["defi"],
    status: "active",
    eventCount: 50,
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  },
];

describe("ContractSearch", () => {
  const mockOnChange = jest.fn();
  const mockOnSelect = jest.fn();

  beforeEach(() => {
    mockOnChange.mockClear();
    mockOnSelect.mockClear();
  });

  it("renders search input with placeholder", () => {
    render(
      <ContractSearch
        contracts={mockContracts}
        value=""
        onChange={mockOnChange}
        placeholder="Search contracts..."
      />
    );
    expect(screen.getByPlaceholderText("Search contracts...")).toBeInTheDocument();
  });

  it("shows autocomplete suggestions when typing", async () => {
    const user = userEvent.setup();
    render(
      <ContractSearch
        contracts={mockContracts}
        value="swap"
        onChange={mockOnChange}
      />
    );

    const input = screen.getByRole("combobox");
    await user.click(input);

    expect(screen.getByRole("listbox")).toBeInTheDocument();
    expect(screen.getByText("Swap Pool")).toBeInTheDocument();
  });

  it("calls onSelect when a suggestion is clicked", async () => {
    const user = userEvent.setup();
    render(
      <ContractSearch
        contracts={mockContracts}
        value="swap"
        onChange={mockOnChange}
        onSelect={mockOnSelect}
      />
    );

    await user.click(screen.getByRole("combobox"));
    await user.click(screen.getByText("Swap Pool"));
    expect(mockOnSelect).toHaveBeenCalledWith(mockContracts[1]);
    expect(mockOnChange).toHaveBeenCalledWith("Swap Pool");
  });

  it("navigates suggestions with arrow keys and selects with Enter", () => {
    render(
      <ContractSearch
        contracts={mockContracts}
        value="st"
        onChange={mockOnChange}
        onSelect={mockOnSelect}
      />
    );

    const input = screen.getByRole("combobox");
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(mockOnSelect).toHaveBeenCalled();
  });

  it("clears search when clear button is clicked", async () => {
    const user = userEvent.setup();
    render(
      <ContractSearch
        contracts={mockContracts}
        value="swap"
        onChange={mockOnChange}
      />
    );

    await user.click(screen.getByLabelText("Clear search"));
    expect(mockOnChange).toHaveBeenCalledWith("");
  });

  it("closes suggestions on Escape", async () => {
    const user = userEvent.setup();
    render(
      <ContractSearch
        contracts={mockContracts}
        value="swap"
        onChange={mockOnChange}
      />
    );

    const input = screen.getByRole("combobox");
    await user.click(input);
    expect(screen.getByRole("listbox")).toBeInTheDocument();

    fireEvent.keyDown(input, { key: "Escape" });
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});
