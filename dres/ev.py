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
        self.schedule_type = "unknown"
        
    
    def load_ev_data(self, ev_data_file=None):
        """Quick load of EV data."""
        
        t0 = performance()

        # Parsing options
        if ev_data_file == "processed_ev_usage.csv":
            spaghetti_model = True
        else:
            spaghetti_model = False

        # Full path to file
        full_filename = os.path.join(self.parent.paths.inputs, ev_data_file)

        # Open csv
        df = pd.read_csv(full_filename)

        # Create column with complete DateTime obj for Arrival and Departure
        if spaghetti_model:
            # Spaghetti model
            df['Departure DateTime'] = [pd.to_datetime(f"2018-12-31 {row['Departure Time']}") + pd.Timedelta(days=row.Day-1) for (i,row) in df.iterrows()]
            df['Arrival DateTime'] = [pd.to_datetime(f"2018-12-31 {row['Arrival Time']}") + pd.Timedelta(days=row.Day-1) for (i,row) in df.iterrows()]

            df.drop(columns=['Day', 'Departure Time', 'Arrival Time', 'Departure Full Time', 'Arrival Full Time', 'Distance (km)', 'SOC_cost'], inplace=True)

            rename_map = {
                "vehicle": "ev_id",
            }

            df = df.rename(columns=rename_map)
            self.schedule_type = "journey_schedule"

        else:
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