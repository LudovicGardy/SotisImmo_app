### Absolute imports
import streamlit as st
import streamlit_analytics
import requests
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import numpy as np
import pandas as pd
import platform
import tempfile
import json
import sys

### Relative imports
from modules.config import firebase_credentials, page_config, data_URL
from modules.plots import Plotter
from modules.data_loader import load_summarized_data, fetch_data_gouv
cred_dict = firebase_credentials()
data_gouv_dict = data_URL()

if cred_dict:
    ### Secure way to store the firestore keys and provide them to start_tracking
    tfile = tempfile.NamedTemporaryFile(mode='w+')
    json.dump(cred_dict, tfile)
    tfile.flush()
    streamlit_analytics.start_tracking(firestore_key_file=tfile.name, firestore_collection_name='sotisimmo_analytics')
else:
    print("No credentials were found. Analytics will not be tracked.")

### App
class PropertyApp(Plotter):
    '''
    This class creates a Streamlit app that displays the average price of real estate properties in France, by department.
    The data is loaded from the French open data portal (https://www.data.gouv.fr/fr/), and the app is built with Streamlit.
    The app is not optimized for mobile devices, and the data is limited to the years 2018-2023. A new version will be released
    in the future, with more features and a better user experience. A streaming version of the app will come soon as well, with
    a Kafka cluster and a Spark Streaming job. Stay tuned! 

    Parameters
    ----------
    None

    Returns
    -------
    A Streamlit app
    '''
    
    def __init__(self):
        '''
        Initialize the app.
        '''
        
        print("Init the app...")

        ### Set page config
        st.set_page_config(page_title=page_config().get('page_title'), 
                            page_icon = page_config().get('page_icon'),  
                            layout = page_config().get('layout'),
                            initial_sidebar_state = page_config().get('initial_sidebar_state'))
        st.markdown(page_config().get('markdown'), unsafe_allow_html=True)

        ### Init parameters
        self.jitter_value = 0
        self.data_loaded = True  # Variable to check if the data has been loaded

        if 'selected_postcode_title' not in st.session_state:
            st.session_state.selected_postcode_title = None

        self.summarized_df_pandas = load_summarized_data()

        with st.sidebar:
            self.steup_sidebar()
            self.initial_request()

        self.create_plots()


    def steup_sidebar(self):
        '''
        Set up the sidebar.
        '''

        logo_path = page_config().get('page_logo')
        desired_width = 60

        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.image(logo_path, width=desired_width)
        with col2:
            st.write('# Sotis A.I.')

        st.caption('''Ce prototype propose de répondre à un besoin de lecture plus claire du marché immobilier. 
                   \nRendez-vous sur https://www.sotisanalytics.com pour en savoir plus, signaler un problème, une idée ou pour me contacter. Bonne visite ! 
                   \nSotis A.I.© 2023''')


        st.divider()

    def initial_request(self):
        '''
        Load data from the French open data portal and initialize the parameters of the app.

        Parameters
        ----------
        None

        Returns
        -------
        self.df_pandas: Pandas dataframe
            The dataframe containing the data loaded from the French open data portal.
        self.selected_department: str
            The department selected by the user.
        self.selected_year: str
            The year selected by the user.
        self.selected_property_type: str
            The property type selected by the user.
        self.selected_mapbox_style: str
            The map style selected by the user.
        self.selected_colormap: str
            The colormap selected by the user.
        '''

        ### Set up the department selectbox
        departments = [str(i).zfill(2) for i in range(1, 96)]
        departments.extend(['971', '972', '973', '974', '2A', '2B'])
        default_dept = departments.index('06')
        self.selected_department = st.selectbox('Département', departments, index=default_dept)

        # Check if the department has changed and reset the session state for the postcode if needed
        if 'previous_selected_department' in st.session_state and st.session_state.previous_selected_department != self.selected_department:
            if 'selected_postcode_title' in st.session_state:
                del st.session_state.selected_postcode_title
            if 'selected_postcode' in st.session_state:
                del st.session_state.selected_postcode

        # Update the previous selected department in the session state
        st.session_state.previous_selected_department = self.selected_department

        ### Set up the year selectbox
        # default_year = data_gouv_dict.get('data_gouv_years').index(data_gouv_dict.get('data_gouv_years')[-1])
        years = [f'Vendus en {year}' for year in data_gouv_dict.get('data_gouv_years')]
        default_year = years.index('Vendus en 2023')        
        self.selected_year = st.selectbox('Année', years, index=default_year).split(' ')[-1]

        ### Load data
        self.df_pandas = fetch_data_gouv(self.selected_department, self.selected_year)

        if not self.df_pandas is None:

            ### Set up a copy of the dataframe
            self.df_pandas = self.df_pandas.copy()

            ### Set up the property type selectbox
            property_types = sorted(self.df_pandas['type_local'].unique())
            selectbox_key = f'local_type_{self.selected_department}_{self.selected_year}'
            self.selected_property_type = st.selectbox('Type de bien', property_types, key=selectbox_key)

            ### Set up the normalization checkbox
            self.normalize_by_area = st.checkbox('Prix au m²', True)
            
            if self.normalize_by_area:
                self.df_pandas['valeur_fonciere'] = self.df_pandas['valeur_fonciere'] / self.df_pandas['surface_reelle_bati']

            # Ajoutez ceci après les autres éléments dans la barre latérale
            self.selected_plots = st.multiselect('Supprimer / ajouter des graphiques', 
                                                ['Carte', 'Fig. 1', 'Fig. 2', 'Fig. 3', 'Fig. 4'],
                                                ['Carte', 'Fig. 1', 'Fig. 2', 'Fig. 3', 'Fig. 4'])

if cred_dict:
    streamlit_analytics.stop_tracking(firestore_key_file=tfile.name, firestore_collection_name='sotisimmo_analytics')

if __name__ == '__main__':
    PropertyApp()