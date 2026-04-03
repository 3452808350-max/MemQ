"""Result aggregation module."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import pandas as pd

from .phone_validator import PhoneValidationResult, ValidityStatus
from .whatsapp_checker import WhatsAppCheckResult, WhatsAppStatus
from .logger import setup_logging, ProcessingStats

logger = setup_logging()


@dataclass
class AggregatedResult:
    """Aggregated result for a single phone number."""
    original_number: str
    cleaned_number: Optional[str]
    e164_number: Optional[str]
    country_code: Optional[str]
    parse_status: str
    validity_status: str
    whatsapp_status: str
    error_message: Optional[str]
    formatted_national: Optional[str] = None
    formatted_international: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class ResultAggregator:
    """
    Aggregates validation and WhatsApp check results.
    
    Combines:
    - Phone validation results
    - WhatsApp check results
    - Original data from input
    """
    
    def __init__(self, stats: Optional[ProcessingStats] = None):
        """
        Initialize result aggregator.
        
        Args:
            stats: Processing stats tracker (optional)
        """
        self.stats = stats
    
    def aggregate(
        self,
        phone_results: List[PhoneValidationResult],
        wa_results: List[WhatsAppCheckResult],
        original_df: Optional[pd.DataFrame] = None,
        extra_columns: Optional[List[str]] = None
    ) -> List[AggregatedResult]:
        """
        Aggregate validation and WhatsApp results.
        
        Args:
            phone_results: List of phone validation results
            wa_results: List of WhatsApp check results
            original_df: Original DataFrame with extra columns
            extra_columns: List of extra column names to include
            
        Returns:
            List of AggregatedResult objects
        """
        results = []
        
        # Check for length mismatch
        if len(phone_results) != len(wa_results):
            logger.warning(
                f"Result length mismatch: {len(phone_results)} phone results vs "
                f"{len(wa_results)} WhatsApp results. Using min length."
            )
        
        # Use zip with strict=False to handle mismatched lengths gracefully
        min_length = min(len(phone_results), len(wa_results))
        
        for i in range(min_length):
            phone_result = phone_results[i]
            wa_result = wa_results[i]
            # Get extra data from original DataFrame
            extra_data = None
            if original_df is not None and extra_columns:
                extra_data = {}
                for col in extra_columns:
                    if col in original_df.columns and i < len(original_df):
                        extra_data[col] = original_df.iloc[i].get(col)
            
            # Create aggregated result
            aggregated = AggregatedResult(
                original_number=phone_result.original_number,
                cleaned_number=phone_result.cleaned_number,
                e164_number=phone_result.e164_number,
                country_code=phone_result.country_code,
                parse_status=phone_result.parse_status.value,
                validity_status=phone_result.validity_status.value,
                whatsapp_status=wa_result.status.value,
                error_message=phone_result.error_message or wa_result.error_message,
                formatted_national=phone_result.formatted_national,
                formatted_international=phone_result.formatted_international,
                extra_data=extra_data
            )
            
            results.append(aggregated)
            
            # Update stats
            if self.stats:
                self.stats.record_valid() if phone_result.validity_status == ValidityStatus.VALID \
                    else self.stats.record_invalid() if phone_result.validity_status == ValidityStatus.INVALID \
                    else self.stats.record_unparseable()
        
        # Handle any remaining phone_results without matching wa_results
        if len(phone_results) > min_length:
            logger.warning(f"{len(phone_results) - min_length} phone results without matching WhatsApp results")
            for i in range(min_length, len(phone_results)):
                phone_result = phone_results[i]
                # Create a default "unknown" WhatsApp result
                from .whatsapp_checker import WhatsAppCheckResult, WhatsAppStatus
                wa_result = WhatsAppCheckResult(
                    phone_number=phone_result.e164_number or '',
                    status=WhatsAppStatus.UNKNOWN,
                    source='aggregator',
                    error_message='Missing WhatsApp check result'
                )
                
                extra_data = None
                if original_df is not None and extra_columns and i < len(original_df):
                    extra_data = {col: original_df.iloc[i].get(col) for col in extra_columns if col in original_df.columns}
                
                aggregated = AggregatedResult(
                    original_number=phone_result.original_number,
                    cleaned_number=phone_result.cleaned_number,
                    e164_number=phone_result.e164_number,
                    country_code=phone_result.country_code,
                    parse_status=phone_result.parse_status.value,
                    validity_status=phone_result.validity_status.value,
                    whatsapp_status=wa_result.status.value,
                    error_message=f"{phone_result.error_message or ''}; {wa_result.error_message}".strip('; '),
                    formatted_national=phone_result.formatted_national,
                    formatted_international=phone_result.formatted_international,
                    extra_data=extra_data
                )
                results.append(aggregated)
                
                if self.stats:
                    self.stats.record_valid() if phone_result.validity_status == ValidityStatus.VALID \
                        else self.stats.record_invalid() if phone_result.validity_status == ValidityStatus.INVALID \
                        else self.stats.record_unparseable()
        
        return results
    
    def to_dataframe(
        self, 
        results: List[AggregatedResult],
        include_extra_columns: bool = True
    ) -> pd.DataFrame:
        """
        Convert aggregated results to DataFrame.
        
        Args:
            results: List of AggregatedResult objects
            include_extra_columns: Whether to include extra columns
            
        Returns:
            DataFrame with all results
        """
        rows = []
        
        for result in results:
            row = {
                'original_number': result.original_number,
                'cleaned_number': result.cleaned_number,
                'e164_number': result.e164_number,
                'country_code': result.country_code,
                'parse_status': result.parse_status,
                'validity_status': result.validity_status,
                'whatsapp_status': result.whatsapp_status,
                'error_message': result.error_message,
                'formatted_national': result.formatted_national,
                'formatted_international': result.formatted_international
            }
            
            # Add extra columns
            if include_extra_columns and result.extra_data:
                row.update(result.extra_data)
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # Reorder columns to put important ones first
        column_order = [
            'original_number',
            'cleaned_number',
            'e164_number',
            'validity_status',
            'whatsapp_status',
            'country_code',
            'parse_status',
            'error_message',
            'formatted_national',
            'formatted_international'
        ]
        
        # Add any extra columns at the end
        if len(df.columns) > len(column_order):
            extra_cols = [c for c in df.columns if c not in column_order]
            column_order.extend(extra_cols)
        
        # Only keep columns that exist
        column_order = [c for c in column_order if c in df.columns]
        
        return df[column_order]
    
    def generate_summary(self, results: List[AggregatedResult]) -> Dict[str, Any]:
        """
        Generate summary statistics from results.
        
        Args:
            results: List of AggregatedResult objects
            
        Returns:
            Dictionary with summary statistics
        """
        total = len(results)
        
        valid_count = sum(1 for r in results if r.validity_status == ValidityStatus.VALID.value)
        invalid_count = sum(1 for r in results if r.validity_status == ValidityStatus.INVALID.value)
        unparseable_count = sum(1 for r in results if r.validity_status == ValidityStatus.UNPARSEABLE.value)
        
        wa_yes = sum(1 for r in results if r.whatsapp_status == WhatsAppStatus.YES.value)
        wa_no = sum(1 for r in results if r.whatsapp_status == WhatsAppStatus.NO.value)
        wa_unknown = sum(1 for r in results if r.whatsapp_status == WhatsAppStatus.UNKNOWN.value)
        
        return {
            'total_numbers': total,
            'valid_numbers': valid_count,
            'invalid_numbers': invalid_count,
            'unparseable_numbers': unparseable_count,
            'validity_rate': round(valid_count / total * 100, 2) if total > 0 else 0,
            'whatsapp_found': wa_yes,
            'whatsapp_not_found': wa_no,
            'whatsapp_unknown': wa_unknown,
            'whatsapp_rate': round(wa_yes / total * 100, 2) if total > 0 else 0
        }