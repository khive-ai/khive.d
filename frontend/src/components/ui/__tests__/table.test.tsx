/**
 * Table Component Tests
 */

import { render, screen } from "@testing-library/react";
import { Column, Table } from "../table";
import { CustomThemeProvider } from "@/lib/providers/theme-provider";

interface TestData {
  id: number;
  name: string;
  status: "active" | "inactive";
  count: number;
}

const mockData: TestData[] = [
  { id: 1, name: "Test Item 1", status: "active", count: 10 },
  { id: 2, name: "Test Item 2", status: "inactive", count: 5 },
  { id: 3, name: "Test Item 3", status: "active", count: 15 },
];

const mockColumns: Column<TestData>[] = [
  {
    id: "id",
    label: "ID",
    accessor: "id",
    sortable: true,
  },
  {
    id: "name",
    label: "Name",
    accessor: "name",
    sortable: true,
  },
  {
    id: "status",
    label: "Status",
    accessor: "status",
    render: (value) => (
      <span style={{ color: value === "active" ? "green" : "red" }}>
        {value}
      </span>
    ),
  },
  {
    id: "count",
    label: "Count",
    accessor: "count",
    align: "right",
  },
];

function TableWrapper({ children }: { children: React.ReactNode }) {
  return (
    <CustomThemeProvider>
      {children}
    </CustomThemeProvider>
  );
}

describe("Table Component", () => {
  it("renders table with data", () => {
    render(
      <TableWrapper>
        <Table columns={mockColumns} data={mockData} paginated={false} />
      </TableWrapper>,
    );

    expect(screen.getByText("ID")).toBeInTheDocument();
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
    expect(screen.getByText("Count")).toBeInTheDocument();

    expect(screen.getByText("Test Item 1")).toBeInTheDocument();
    expect(screen.getByText("Test Item 2")).toBeInTheDocument();
    expect(screen.getByText("Test Item 3")).toBeInTheDocument();
  });

  it("renders empty state when no data", () => {
    render(
      <TableWrapper>
        <Table
          columns={mockColumns}
          data={[]}
          emptyMessage="No items found"
        />
      </TableWrapper>,
    );

    expect(screen.getByText("No items found")).toBeInTheDocument();
  });

  it("renders loading state", () => {
    render(
      <TableWrapper>
        <Table columns={mockColumns} data={mockData} loading={true} />
      </TableWrapper>,
    );

    // Table headers should still be visible during loading
    expect(screen.getByText("ID")).toBeInTheDocument();
    expect(screen.getByText("Name")).toBeInTheDocument();
  });

  it("renders selectable rows when selectable is true", () => {
    render(
      <TableWrapper>
        <Table
          columns={mockColumns}
          data={mockData}
          selectable={true}
          paginated={false}
        />
      </TableWrapper>,
    );

    // Should have checkboxes (one for select all + one for each row)
    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes).toHaveLength(mockData.length + 1);
  });

  it("renders custom cell content", () => {
    render(
      <TableWrapper>
        <Table columns={mockColumns} data={mockData} paginated={false} />
      </TableWrapper>,
    );

    // Status column should render custom content
    expect(screen.getByText("active")).toBeInTheDocument();
    expect(screen.getByText("inactive")).toBeInTheDocument();
  });
});
