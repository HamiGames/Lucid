import React from 'react';

interface PaginationControlsProps {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  itemsPerPage: number;
  onPageChange: (page: number) => void;
  onItemsPerPageChange?: (itemsPerPage: number) => void;
  showItemsPerPage?: boolean;
  showPageInfo?: boolean;
  showFirstLast?: boolean;
  maxVisiblePages?: number;
  loading?: boolean;
  className?: string;
}

export const PaginationControls: React.FC<PaginationControlsProps> = ({
  currentPage,
  totalPages,
  totalItems,
  itemsPerPage,
  onPageChange,
  onItemsPerPageChange,
  showItemsPerPage = true,
  showPageInfo = true,
  showFirstLast = true,
  maxVisiblePages = 5,
  loading = false,
  className = ''
}) => {
  const getVisiblePages = () => {
    const pages: (number | string)[] = [];
    const halfVisible = Math.floor(maxVisiblePages / 2);
    
    let startPage = Math.max(1, currentPage - halfVisible);
    let endPage = Math.min(totalPages, currentPage + halfVisible);
    
    // Adjust if we're near the beginning or end
    if (endPage - startPage + 1 < maxVisiblePages) {
      if (startPage === 1) {
        endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
      } else {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
      }
    }
    
    // Add first page and ellipsis if needed
    if (startPage > 1) {
      pages.push(1);
      if (startPage > 2) {
        pages.push('...');
      }
    }
    
    // Add visible pages
    for (let i = startPage; i <= endPage; i++) {
      pages.push(i);
    }
    
    // Add ellipsis and last page if needed
    if (endPage < totalPages) {
      if (endPage < totalPages - 1) {
        pages.push('...');
      }
      pages.push(totalPages);
    }
    
    return pages;
  };

  const handlePageClick = (page: number) => {
    if (page >= 1 && page <= totalPages && page !== currentPage && !loading) {
      onPageChange(page);
    }
  };

  const handleItemsPerPageChange = (newItemsPerPage: number) => {
    if (onItemsPerPageChange && !loading) {
      onItemsPerPageChange(newItemsPerPage);
    }
  };

  const getPageInfo = () => {
    const startItem = (currentPage - 1) * itemsPerPage + 1;
    const endItem = Math.min(currentPage * itemsPerPage, totalItems);
    return `${startItem}-${endItem} of ${totalItems.toLocaleString()}`;
  };

  const canGoPrevious = currentPage > 1 && !loading;
  const canGoNext = currentPage < totalPages && !loading;

  if (totalPages <= 1 && !showItemsPerPage) {
    return null;
  }

  return (
    <div className={`pagination-controls ${className}`}>
      {showPageInfo && (
        <div className="pagination-info">
          <span className="page-info">{getPageInfo()}</span>
        </div>
      )}

      <div className="pagination-navigation">
        {showFirstLast && (
          <button
            className="pagination-btn first"
            onClick={() => handlePageClick(1)}
            disabled={!canGoPrevious || loading}
            title="First page"
          >
            ⏮️
          </button>
        )}

        <button
          className="pagination-btn previous"
          onClick={() => handlePageClick(currentPage - 1)}
          disabled={!canGoPrevious || loading}
          title="Previous page"
        >
          ◀️
        </button>

        <div className="page-numbers">
          {getVisiblePages().map((page, index) => (
            <React.Fragment key={index}>
              {typeof page === 'number' ? (
                <button
                  className={`pagination-btn page ${page === currentPage ? 'active' : ''}`}
                  onClick={() => handlePageClick(page)}
                  disabled={loading}
                  title={`Page ${page}`}
                >
                  {page}
                </button>
              ) : (
                <span className="pagination-ellipsis">{page}</span>
              )}
            </React.Fragment>
          ))}
        </div>

        <button
          className="pagination-btn next"
          onClick={() => handlePageClick(currentPage + 1)}
          disabled={!canGoNext || loading}
          title="Next page"
        >
          ▶️
        </button>

        {showFirstLast && (
          <button
            className="pagination-btn last"
            onClick={() => handlePageClick(totalPages)}
            disabled={!canGoNext || loading}
            title="Last page"
          >
            ⏭️
          </button>
        )}
      </div>

      {showItemsPerPage && onItemsPerPageChange && (
        <div className="pagination-size">
          <label htmlFor="items-per-page">Per page:</label>
          <select
            id="items-per-page"
            value={itemsPerPage}
            onChange={(e) => handleItemsPerPageChange(Number(e.target.value))}
            disabled={loading}
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={250}>250</option>
          </select>
        </div>
      )}

      {loading && (
        <div className="pagination-loading">
          <div className="loading-spinner small"></div>
        </div>
      )}
    </div>
  );
};

export default PaginationControls;
