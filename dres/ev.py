import pandas as pd
from dres.dafni_utilities import performance
from dres import ev_optimise
import os


# EV data container class
class EV():
    def __init__(self, parent):
        self.parent = parent
        self.schedule_data = pd.DataFrame()
        self.soc_timeline = pd.DataFrame()
        self.schedule_type = self.parent.simulation_config['EV_schedule_data']['schedule_type'].strip().lower()

        # Load data if available
        if 'EV_schedule_data' in self.parent.simulation_config:
            self.load_ev_data()  # Load

        
    
    def load_ev_data(self):
        """Quick load of EV data."""
        
        t0 = performance()

        # Parsing options
        if self.schedule_type not in {"journey_events", "charge_events", "soc_timeline", "station_timeline"}:
            raise ValueError(
                "schedule_type must be 'journey_events', 'charge_events', 'soc_timeline' or 'station_timeline"
            )
        
        # Full path to file
        full_filename = os.path.join(
            self.parent.paths.inputs, 
            self.parent.simulation_config['EV_schedule_data']['filename']
        )

        # Open csv
        df = pd.read_csv(full_filename)

        # Map columns to standard names
        column_mapping = self.parent.simulation_config['EV_schedule_data']['column_name_mappings']
        column_mapping = {v: k for k, v in column_mapping.items()} # Reverse the mapping
        df = df[[col for col in df.columns if col in column_mapping.keys()]].copy()
        df.rename(columns=column_mapping, inplace=True)

        # Determine if we need to evaluate end datetime from start+duration
        evaluate_datetime_end_from_duration = self.parent.simulation_config['EV_schedule_data'].get('evaluate_datetime_end_from_duration', False)
        if evaluate_datetime_end_from_duration:
            # Evaluate DateTime and Duration columns
            df['datetime_charge_start'] = pd.to_datetime(df['datetime_charge_start'], format='%d/%m/%Y %I:%M:%S %p')
            df['time_charge_duration'] = pd.to_timedelta(df['time_charge_duration'])
            df['dateime_charge_end'] = df['datetime_charge_start'] + df['time_charge_duration']

            
        if 'include_date_datum' in self.parent.simulation_config['EV_schedule_data']:
            if "datetime" in df.columns:
                base_date = pd.Timestamp(self.parent.simulation_config['EV_schedule_data']['include_date_datum'])
    
                df["datetime"] = pd.to_datetime(
                    df["datetime"],
                    unit="s",
                    origin=base_date
                )

        # Convert all datetime columns to datetime format
        datetime_columns = [col for col in df.columns if "datetime" in col.lower()]
        for col in datetime_columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
                
        self.schedule_data = df
        performance(t0)
        return
    

    def list_most_common_ev_entries(self):
        """Return DataFrame of most common EV entries in schedule data."""
        if self.schedule_data.empty:
            raise ValueError("No EV schedule data loaded. Please load data first.")
        
        most_common = self.schedule_data['ev_id'].value_counts()
        df_result = pd.DataFrame({
            'ev_id': most_common.index,
            'entries': most_common.values
        }).reset_index(drop=True)
        
        return df_result

    def list_most_common_vehicle_ids(self, top_n=20, id_column="ev_id"):
        """Return DataFrame of most common vehicle IDs in schedule data."""
        if self.schedule_data.empty:
            raise ValueError("No EV schedule data loaded. Please load data first.")

        if id_column not in self.schedule_data.columns:
            raise KeyError(
                f"Column '{id_column}' not found in schedule_data. "
                f"Available columns: {list(self.schedule_data.columns)}"
            )

        most_common = self.schedule_data[id_column].value_counts().head(top_n)
        df_result = pd.DataFrame({
            id_column: most_common.index,
            "entries": most_common.values
        }).reset_index(drop=True)

        return df_result