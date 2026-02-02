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

        if self.schedule_type == "charge_events":
            # Data
            # Evaluate DateTime and Duration columns
            df['ChargeEventStartDate'] = pd.to_datetime(df['ChargeEventStartDate'], format='%d/%m/%Y %I:%M:%S %p')
            df['ChargeEventDuration'] = pd.to_timedelta(df['ChargeEventDuration'])
            df['ChargeEventEndDate'] = df['ChargeEventStartDate'] + df['ChargeEventDuration']

            column_name_mappings = {
                'DeviceName': 'ev_id',
                'ChargeEventStartDate': 'charge_event_start',
                'ChargeEventEndDate': 'charge_event_end',
                'ChargeEventStartCharge': 'charge_event_start_soc',
                'ChargeEventEndCharge': 'charge_event_end_soc',
            }

            df = df.rename(columns=column_name_mappings)
            df = df[['ev_id', 'charge_event_start', 'charge_event_end', 'charge_event_start_soc', 'charge_event_end_soc']].copy()
            """
            df = df[['DeviceName', 'ChargeEventStartDate', 'ChargeEventEndDate', 'ChargeEventStartCharge', 'ChargeEventEndCharge']].copy()
            """
            self.schedule_type = "charge_event_schedule"

        elif self.schedule_type == "soc_timeline":
            None

        if 'include_date_datum' in self.parent.simulation_config['EV_schedule_data']:
            if "datetime" in df.columns:
                base_date = pd.Timestamp(self.parent.simulation_config['EV_schedule_data']['include_date_datum'])
    
                df["datetime"] = pd.to_datetime(
                    df["datetime"],
                    unit="s",
                    origin=base_date
                )
                
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