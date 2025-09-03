/**
 * Table components built with React Table and Material-UI
 * Provides advanced table functionality with sorting, filtering, and pagination
 */

import * as React from "react";
import {
  Box,
  Checkbox,
  Chip,
  IconButton,
  InputAdornment,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Paper,
  Skeleton,
  Stack,
  Table as MuiTable,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  TextField,
  Typography,
  useTheme,
} from "@mui/material";
import {
  Delete as DeleteIcon,
  Edit as EditIcon,
  FilterList as FilterIcon,
  MoreVert as MoreIcon,
  Search as SearchIcon,
  Visibility as ViewIcon,
} from "@mui/icons-material";
import {
  type ColumnDef,
  type ColumnFiltersState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  type RowSelectionState,
  type SortingState,
  useReactTable,
  type VisibilityState,
} from "@tanstack/react-table";
import { cn } from "@/lib/utils";

// Table component interfaces
export interface TableAction<T = any> {
  label: string;
  icon?: React.ReactNode;
  onClick: (data: T) => void;
  color?:
    | "inherit"
    | "primary"
    | "secondary"
    | "error"
    | "info"
    | "success"
    | "warning";
  disabled?: (data: T) => boolean;
}

export interface DataTableProps<T = any> {
  data: T[];
  columns: ColumnDef<T>[];
  loading?: boolean;
  searchable?: boolean;
  searchPlaceholder?: string;
  filterable?: boolean;
  selectable?: boolean;
  actions?: TableAction<T>[];
  onRowClick?: (data: T) => void;
  pagination?: boolean;
  pageSize?: number;
  className?: string;
  stickyHeader?: boolean;
  emptyStateMessage?: string;
  emptyStateDescription?: string;
}

// Loading skeleton component
const TableSkeleton: React.FC<{ rows?: number; columns?: number }> = ({
  rows = 5,
  columns = 4,
}) => (
  <TableContainer>
    <MuiTable>
      <TableHead>
        <TableRow>
          {Array.from({ length: columns }).map((_, index) => (
            <TableCell key={index}>
              <Skeleton variant="text" width="80%" />
            </TableCell>
          ))}
        </TableRow>
      </TableHead>
      <TableBody>
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <TableRow key={rowIndex}>
            {Array.from({ length: columns }).map((_, colIndex) => (
              <TableCell key={colIndex}>
                <Skeleton
                  variant="text"
                  width={colIndex === 0 ? "60%" : "40%"}
                />
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </MuiTable>
  </TableContainer>
);

// Empty state component
const EmptyState: React.FC<{ message?: string; description?: string }> = ({
  message = "No data available",
  description,
}) => (
  <Box
    sx={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      py: 8,
      textAlign: "center",
    }}
  >
    <Typography variant="h6" color="text.secondary" gutterBottom>
      {message}
    </Typography>
    {description && (
      <Typography variant="body2" color="text.secondary">
        {description}
      </Typography>
    )}
  </Box>
);

// Row actions menu component
const RowActionsMenu: React.FC<{
  actions: TableAction[];
  data: any;
}> = ({ actions, data }) => {
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleAction = (action: TableAction) => {
    action.onClick(data);
    handleClose();
  };

  return (
    <>
      <IconButton size="small" onClick={handleClick}>
        <MoreIcon />
      </IconButton>
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleClose}
        onClick={(e) => e.stopPropagation()}
      >
        {actions.map((action, index) => (
          <MenuItem
            key={index}
            onClick={() => handleAction(action)}
            disabled={action.disabled?.(data)}
          >
            {action.icon && (
              <ListItemIcon>
                {action.icon}
              </ListItemIcon>
            )}
            <ListItemText>{action.label}</ListItemText>
          </MenuItem>
        ))}
      </Menu>
    </>
  );
};

// Main DataTable component
export const DataTable = <T,>({
  data,
  columns,
  loading = false,
  searchable = false,
  searchPlaceholder = "Search...",
  filterable = false,
  selectable = false,
  actions = [],
  onRowClick,
  pagination = true,
  pageSize = 10,
  className,
  stickyHeader = false,
  emptyStateMessage,
  emptyStateDescription,
}: DataTableProps<T>) => {
  const theme = useTheme();
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>(
    [],
  );
  const [columnVisibility, setColumnVisibility] = React.useState<
    VisibilityState
  >({});
  const [rowSelection, setRowSelection] = React.useState<RowSelectionState>({});
  const [globalFilter, setGlobalFilter] = React.useState("");

  // Add actions column if actions are provided
  const finalColumns = React.useMemo(() => {
    const baseColumns = [...columns];

    // Add selection column if selectable
    if (selectable) {
      baseColumns.unshift({
        id: "select",
        header: ({ table }) => (
          <Checkbox
            checked={table.getIsAllPageRowsSelected()}
            indeterminate={table.getIsSomePageRowsSelected()}
            onChange={(event) =>
              table.toggleAllPageRowsSelected(event.target.checked)}
            color="primary"
          />
        ),
        cell: ({ row }) => (
          <Checkbox
            checked={row.getIsSelected()}
            disabled={!row.getCanSelect()}
            indeterminate={row.getIsSomeSelected()}
            onChange={(event) => row.toggleSelected(event.target.checked)}
            color="primary"
          />
        ),
        enableSorting: false,
        enableColumnFilter: false,
      } as ColumnDef<T>);
    }

    // Add actions column if actions are provided
    if (actions.length > 0) {
      baseColumns.push({
        id: "actions",
        header: "Actions",
        cell: ({ row }) => (
          <RowActionsMenu actions={actions} data={row.original} />
        ),
        enableSorting: false,
        enableColumnFilter: false,
      } as ColumnDef<T>);
    }

    return baseColumns;
  }, [columns, selectable, actions]);

  const table = useReactTable({
    data,
    columns: finalColumns,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
      globalFilter,
    },
    enableRowSelection: selectable,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: pagination ? getPaginationRowModel() : undefined,
    getSortedRowModel: getSortedRowModel(),
    initialState: {
      pagination: {
        pageSize,
      },
    },
  });

  if (loading) {
    return <TableSkeleton />;
  }

  if (!loading && data.length === 0) {
    return (
      <Paper className={className}>
        <EmptyState
          message={emptyStateMessage}
          description={emptyStateDescription}
        />
      </Paper>
    );
  }

  return (
    <Paper className={className}>
      {/* Search and Filter Controls */}
      {(searchable || filterable) && (
        <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}` }}>
          <Stack direction="row" spacing={2} alignItems="center">
            {searchable && (
              <TextField
                placeholder={searchPlaceholder}
                variant="outlined"
                size="small"
                value={globalFilter}
                onChange={(e) => setGlobalFilter(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon />
                    </InputAdornment>
                  ),
                }}
                sx={{ minWidth: 200 }}
              />
            )}
            {filterable && (
              <IconButton size="small">
                <FilterIcon />
              </IconButton>
            )}
          </Stack>
        </Box>
      )}

      {/* Table */}
      <TableContainer>
        <MuiTable stickyHeader={stickyHeader}>
          <TableHead>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableCell
                    key={header.id}
                    sortDirection={header.column.getIsSorted() === "asc"
                      ? "asc"
                      : header.column.getIsSorted() === "desc"
                      ? "desc"
                      : false}
                  >
                    {header.isPlaceholder ? null : (
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          cursor: header.column.getCanSort()
                            ? "pointer"
                            : "default",
                        }}
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        {header.column.getCanSort()
                          ? (
                            <TableSortLabel
                              active={!!header.column.getIsSorted()}
                              direction={header.column.getIsSorted() === "asc"
                                ? "asc"
                                : "desc"}
                            >
                              {flexRender(
                                header.column.columnDef.header,
                                header.getContext(),
                              )}
                            </TableSortLabel>
                          )
                          : (
                            flexRender(
                              header.column.columnDef.header,
                              header.getContext(),
                            )
                          )}
                      </Box>
                    )}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableHead>
          <TableBody>
            {table.getRowModel().rows.map((row) => (
              <TableRow
                key={row.id}
                selected={row.getIsSelected()}
                hover={!!onRowClick}
                onClick={onRowClick
                  ? () => onRowClick(row.original)
                  : undefined}
                sx={{
                  cursor: onRowClick ? "pointer" : "default",
                }}
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </MuiTable>
      </TableContainer>

      {/* Pagination */}
      {pagination && (
        <TablePagination
          component="div"
          count={table.getFilteredRowModel().rows.length}
          page={table.getState().pagination.pageIndex}
          onPageChange={(_, page) => table.setPageIndex(page)}
          rowsPerPage={table.getState().pagination.pageSize}
          onRowsPerPageChange={(event) =>
            table.setPageSize(Number(event.target.value))}
          rowsPerPageOptions={[5, 10, 25, 50]}
        />
      )}
    </Paper>
  );
};

// Simple table component for basic use cases
export interface SimpleTableProps {
  headers: string[];
  rows: (React.ReactNode | string)[][];
  loading?: boolean;
  className?: string;
}

export const SimpleTable: React.FC<SimpleTableProps> = ({
  headers,
  rows,
  loading = false,
  className,
}) => {
  if (loading) {
    return <TableSkeleton rows={rows.length} columns={headers.length} />;
  }

  return (
    <TableContainer component={Paper} className={className}>
      <MuiTable>
        <TableHead>
          <TableRow>
            {headers.map((header, index) => (
              <TableCell key={index}>{header}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, rowIndex) => (
            <TableRow key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <TableCell key={cellIndex}>{cell}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </MuiTable>
    </TableContainer>
  );
};

// Status cell component for common use cases
export interface StatusCellProps {
  status: string;
  variant?: "default" | "dot";
  color?:
    | "default"
    | "primary"
    | "secondary"
    | "error"
    | "info"
    | "success"
    | "warning";
}

export const StatusCell: React.FC<StatusCellProps> = ({
  status,
  variant = "default",
  color = "default",
}) => (
  <Chip
    label={status}
    size="small"
    color={color}
    variant={variant === "dot" ? "outlined" : "filled"}
  />
);

// Export table types and utilities
export type { ColumnDef, TableAction };
export { flexRender } from "@tanstack/react-table";
