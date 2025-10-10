# integrations/sheet_optimizer.py

import logging
from typing import Dict, List, Optional, Tuple, Any

from integrations.sheet_utils import retry_until_successful, index_to_column


class SheetDataOptimizer:
    """
    Optimized sheet data operations to minimize API calls and avoid rate limiting.
    """

    @staticmethod
    async def fetch_sheet_data_batch(sheet, max_column: str, max_row: int) -> List[List[str]]:
        """
        Fetch all sheet data in a single batch operation.

        Args:
            sheet: gspread worksheet object
            max_column: Maximum column letter (e.g., 'K')
            max_row: Maximum row number to fetch

        Returns:
            2D array of sheet data
        """
        try:
            # Fetch the entire range in one API call
            range_str = f"A1:{max_column}{max_row}"
            logging.info(f"Fetching sheet data range: {range_str}")

            data = await retry_until_successful(sheet.get_all_values, range_str)
            logging.info(f"Fetched {len(data)} rows with {len(data[0]) if data else 0} columns")

            return data

        except Exception as e:
            logging.error(f"Failed to fetch batch sheet data: {e}")
            raise

    @staticmethod
    async def fetch_required_columns_batch(sheet, column_indexes: Dict[str, int], header_row: int, max_players: int) -> Dict[str, List[str]]:
        """
        Fetch only the required columns in a single batch operation.

        Args:
            sheet: gspread worksheet object
            column_indexes: Dictionary mapping column types to column numbers
            header_row: Row number where headers are located
            max_players: Maximum number of players to fetch

        Returns:
            Dictionary mapping column types to column data
        """
        try:
            # Calculate the range we need
            start_row = header_row + 1
            end_row = header_row + max_players

            # Find the maximum column index to determine our range
            max_idx = max(column_indexes.values()) if column_indexes else 1

            # Convert column index to letter
            max_col_letter = index_to_column(max_idx)

            # Fetch the entire data range in one call
            range_str = f"A{start_row}:{max_col_letter}{end_row}"
            logging.info(f"Fetching required columns range: {range_str}")

            data = await retry_until_successful(sheet.get_all_values, range_str)

            # Extract only the columns we need
            result = {}
            for column_type, col_idx in column_indexes.items():
                # Convert 1-based column index to 0-based array index
                array_idx = col_idx - 1

                # Extract this column from each row
                column_data = []
                for row in data:
                    if array_idx < len(row):
                        column_data.append(row[array_idx])
                    else:
                        column_data.append("")

                result[column_type] = column_data

            logging.info(f"Extracted {len(result)} columns from batch fetch")
            return result

        except Exception as e:
            logging.error(f"Failed to fetch required columns batch: {e}")
            raise

    @staticmethod
    async def fetch_headers_batch(sheet, header_row: int, max_columns: int = 20) -> List[str]:
        """
        Fetch all headers in a single operation.

        Args:
            sheet: gspread worksheet object
            header_row: Row number where headers are located
            max_columns: Maximum number of columns to check

        Returns:
            List of header values
        """
        try:
            # Fetch just the header row
            max_col_letter = index_to_column(max_columns)
            range_str = f"A{header_row}:{max_col_letter}{header_row}"

            data = await retry_until_successful(sheet.get_all_values, range_str)

            if data and len(data) > 0:
                headers = data[0]
                logging.info(f"Fetched {len(headers)} headers")
                return headers
            else:
                logging.warning("No header data found")
                return []

        except Exception as e:
            logging.error(f"Failed to fetch headers batch: {e}")
            raise

    @staticmethod
    async def update_cells_batch(sheet, updates: List[Tuple[str, Any]]) -> bool:
        """
        Update multiple cells in a single batch operation.

        Args:
            sheet: gspread worksheet object
            updates: List of (cell_range, value) tuples

        Returns:
            True if successful, False otherwise
        """
        try:
            if not updates:
                return True

            # Group updates by ranges for efficiency
            # For now, we'll update them individually but could be optimized further
            success_count = 0

            for cell_range, value in updates:
                try:
                    await retry_until_successful(sheet.update_acell, cell_range, value)
                    success_count += 1
                except Exception as e:
                    logging.warning(f"Failed to update {cell_range} with {value}: {e}")
                    continue

            logging.info(f"Updated {success_count}/{len(updates)} cells in batch operation")
            return success_count == len(updates)

        except Exception as e:
            logging.error(f"Failed to update cells batch: {e}")
            return False

    @staticmethod
    async def append_row_batch(sheet, row_data: List[Any], max_columns: int = 20) -> bool:
        """
        Append a new row with all data at once.

        Args:
            sheet: gspread worksheet object
            row_data: List of values to append
            max_columns: Maximum number of columns

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure we have the right number of columns
            if len(row_data) < max_columns:
                # Pad with empty strings
                row_data = row_data + [""] * (max_columns - len(row_data))
            elif len(row_data) > max_columns:
                # Truncate to max_columns
                row_data = row_data[:max_columns]

            await retry_until_successful(sheet.append_row, row_data)
            logging.info("Successfully appended new row")
            return True

        except Exception as e:
            logging.error(f"Failed to append row batch: {e}")
            return False

    @staticmethod
    def _index_to_column(index: int) -> str:
        """
        Convert column index to letter (1=A, 2=B, etc.).
        """
        return index_to_column(index)

    @staticmethod
    def calculate_optimal_range(column_indexes: Dict[str, int], header_row: int, max_players: int) -> Tuple[str, int]:
        """
        Calculate the optimal range for fetching data.

        Returns:
            Tuple of (range_string, max_column_index)
        """
        if not column_indexes:
            return f"A{header_row + 1}:A{header_row + max_players}", 1

        max_idx = max(column_indexes.values())
        max_col_letter = index_to_column(max_idx)

        start_row = header_row + 1
        end_row = header_row + max_players

        range_str = f"A{start_row}:{max_col_letter}{end_row}"

        return range_str, max_idx

    @staticmethod
    async def detect_columns_optimized(sheet, header_row: int, max_columns: int = 20) -> List[Tuple[str, int, str]]:
        """
        Optimized column detection that fetches all headers at once.

        Returns:
            List of (column_letter, column_index, header_value) tuples
        """
        try:
            # Fetch all headers in one call
            headers = await SheetDataOptimizer.fetch_headers_batch(sheet, header_row, max_columns)

            result = []
            for idx, header in enumerate(headers, start=1):
                if header and header.strip():
                    col_letter = index_to_column(idx)
                    result.append((col_letter, idx, header.strip()))

            logging.info(f"Detected {len(result)} non-empty headers")
            return result

        except Exception as e:
            logging.error(f"Failed to detect columns optimized: {e}")
            return []


# Global optimizer instance
optimizer = SheetDataOptimizer()


# Convenience functions
async def fetch_sheet_data_batch(sheet, max_column: str, max_row: int) -> List[List[str]]:
    """Convenience function for batch sheet data fetching."""
    return await optimizer.fetch_sheet_data_batch(sheet, max_column, max_row)


async def fetch_required_columns_batch(sheet, column_indexes: Dict[str, int], header_row: int, max_players: int) -> Dict[str, List[str]]:
    """Convenience function for batch column fetching."""
    return await optimizer.fetch_required_columns_batch(sheet, column_indexes, header_row, max_players)


async def update_cells_batch(sheet, updates: List[Tuple[str, Any]]) -> bool:
    """Convenience function for batch cell updates."""
    return await optimizer.update_cells_batch(sheet, updates)


async def detect_columns_optimized(sheet, header_row: int, max_columns: int = 20) -> List[Tuple[str, int, str]]:
    """Convenience function for optimized column detection."""
    return await optimizer.detect_columns_optimized(sheet, header_row, max_columns)