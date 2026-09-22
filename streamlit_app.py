"""Streamlit Community Cloud entry point. Run: streamlit run streamlit_app.py"""
import csv
import io
import os
import sqlite3
import time

import streamlit as st

from app import CATEGORIES, FIELDS, gemini_plan, run_plan
from session_database import SessionDatabase


st.set_page_config(page_title='OSU · P-card Audit', page_icon='🔎', layout='wide')

# Only server-side settings are copied. Never show their values in the interface.
try:
    for key in ('GEMINI_API_KEY', 'GEMINI_MODEL'):
        if key in st.secrets:
            os.environ[key] = str(st.secrets[key])
except FileNotFoundError:
    pass  # Local development can use the existing private .env file.


def clear_results():
    for key in ('dashboard_result', 'questions_result', 'dashboard_csv', 'questions_csv'):
        st.session_state.pop(key, None)


def discard_upload():
    database = st.session_state.pop('audit_database', None)
    if database:
        database.close()
    st.session_state.pop('audit_year', None)
    clear_results()


def search(plan, target, year, page=1):
    st.session_state.pop(target + '_result', None)
    st.session_state.pop(target + '_csv', None)
    try:
        with st.spinner('Searching OSU transactions…'):
            result = run_plan(plan, year, page=page, database_path=st.session_state.audit_database.path)
        st.session_state[target + '_result'] = result
    except ValueError as error:
        st.error(str(error))
    except sqlite3.Error:
        st.error('The database could not be queried. Try a narrower search or upload a valid database again.')


def make_csv(rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]) if rows else FIELDS)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: "'"+v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else v for k, v in row.items()})
    return ('\ufeff' + output.getvalue()).encode('utf-8')


def show_results(target):
    result = st.session_state.get(target + '_result')
    if not result:
        return
    st.divider()
    st.subheader('Matching transactions' if result['plan']['operation'] != 'group' else 'Grouped spending')
    filters = [f'{f["field"]} contains “{f["keyword"]}”' for f in result['plan'].get('filters', [])]
    for key, label in [('min_amount', 'Amount ≥'), ('max_amount', 'Amount ≤')]:
        if result['plan'].get(key) is not None:
            filters.append(f'{label} ${result["plan"][key]:,.2f}')
    st.caption(f'OSU · Calendar year {result["year"]} · ' + (' AND '.join(filters) or 'All transactions in the selected year'))
    metrics = st.columns(3)
    metrics[0].metric('Matching transactions', f'{result["stats"]["count"]:,}')
    metrics[1].metric('Net amount · USD', f'${result["stats"]["total"]:,.2f}')
    metrics[2].metric('Vendors', f'{result["stats"]["vendors"]:,}')
    st.info('Potential exceptions only. Review receipts, business purpose and approvals before reporting a finding. Net amounts include returns and credits.')
    if result['rows']:
        st.dataframe(result['rows'], hide_index=True, width='stretch',
                     column_config={'Amount': st.column_config.NumberColumn('Amount · USD', format='$%.2f')})
        if result['plan']['operation'] == 'group':
            st.caption('First eight groups on this page, sorted by net amount.')
            st.bar_chart(result['rows'][:8], x='GroupName', y='Amount', color='#b64818')
    else:
        st.info('No transactions match. Try a different keyword or calendar year.')
    prev, middle, nxt = st.columns([1, 3, 1])
    prev.button('← Previous', key=target+'_prev', disabled=result['page'] <= 1,
                on_click=search, args=(result['plan'], target, result['year'], result['page']-1))
    middle.caption(f'Page {result["page"]} · Up to 50 rows per page')
    nxt.button('Next →', key=target+'_next', disabled=not result['has_more'],
               on_click=search, args=(result['plan'], target, result['year'], result['page']+1))
    if st.button('Prepare CSV download', key=target+'_prepare'):
        try:
            with st.spinner('Preparing all matching rows…'):
                export = run_plan(result['plan'], result['year'], export=True,
                                  database_path=st.session_state.audit_database.path)
            if export['has_more']:
                st.warning('More than 10,000 rows match. Narrow the search before downloading.')
            else:
                st.session_state[target+'_csv'] = make_csv(export['rows'])
        except (ValueError, sqlite3.Error):
            st.error('The export could not be prepared. Try a narrower search.')
    if target+'_csv' in st.session_state:
        st.download_button('Download CSV ↓', st.session_state[target+'_csv'],
                           file_name=f'osu-{target}-{result["year"]}.csv', mime='text/csv', key=target+'_download')


st.caption('OKLAHOMA STATE UNIVERSITY · PURCHASING CARD REVIEW')
st.title('P-card audit workspace')
st.write('Search potential control deviations and inspect the transaction evidence.')

with st.sidebar:
    st.header('Your transaction database')
    st.caption('Upload pcards.db for this browser session. No website password is required.')
    generation = st.session_state.get('upload_generation', 0)
    uploaded = st.file_uploader('Select pcards.db', type=['db', 'sqlite', 'sqlite3'],
                                key=f'database_upload_{generation}', on_change=discard_upload)
    st.caption('Uploads are processed on the hosting server. This app does not add them to GitHub, share them with other visitor sessions, or send transaction rows to Gemini. Refreshing the page may require another upload.')
    if uploaded is not None and 'audit_database' not in st.session_state:
        try:
            with st.spinner('Checking database and available years…'):
                st.session_state.audit_database = SessionDatabase(uploaded.getbuffer())
        except ValueError as error:
            st.error(str(error))
        except (sqlite3.Error, OSError):
            st.error('This file could not be opened as the expected P-card database.')
    if 'audit_database' in st.session_state:
        st.success('Database ready for this session')
        if st.button('Clear uploaded database'):
            discard_upload()
            st.session_state.upload_generation = generation + 1
            st.rerun()
        years = st.session_state.audit_database.years
        year = st.selectbox('Calendar year', years, index=years.index(2014) if 2014 in years else 0,
                            key='audit_year', on_change=clear_results)
        st.caption('Calendar years are derived from transaction dates. Only OSU transactions are searched.')

if 'audit_database' not in st.session_state:
    st.info('Start by uploading pcards.db using the sidebar. Keep the database out of your public GitHub repository.')
    st.write('After upload, you can ask questions about the database or use separate description and vendor searches to examine possible prohibited purchases.')
    st.stop()

questions, dashboard = st.tabs(['Ask the database', 'Prohibited purchases dashboard'])

with questions:
    st.subheader('Ask a question. Inspect the evidence.')
    st.write('Ask for transaction lists, counts, totals, or spending grouped by vendor, cardholder, merchant category or month. The selected calendar year always applies.')
    st.caption('Examples: “Show transactions with alcohol in the description” · “Show total spending by vendor” · “Show transactions with amounts of at least $5,000”')
    with st.form('question_form'):
        question = st.text_area('Your question', max_chars=1000, placeholder='Show transactions with alcohol in the description')
        asked = st.form_submit_button('Ask the database', type='primary')
    st.caption('Your question is sent to Gemini; transaction rows stay on the server. Do not put confidential details in your question. Review the interpreted filters. Complex tests such as duplicates and split purchases are not supported here.')
    if asked:
        st.session_state.pop('questions_result', None)
        st.session_state.pop('questions_csv', None)
        now = time.monotonic()
        calls = [t for t in st.session_state.get('question_times', []) if now-t < 600]
        if not question.strip():
            st.error('Enter a question first.')
        elif len(calls) >= 15:
            st.warning('Question limit reached for this session. Wait ten minutes or use the dashboard.')
        else:
            st.session_state.question_times = calls + [now]
            try:
                with st.spinner('Interpreting your question…'):
                    plan = gemini_plan(question.strip())
                search(plan, 'questions', year)
            except ValueError as error:
                st.error(str(error))
    show_results('questions')

with dashboard:
    st.subheader('Prohibited purchases')
    with st.expander('How to use this dashboard', expanded=True):
        st.write('1. Select a calendar year in the sidebar.\n2. Choose a policy category to see suggested keywords.\n3. Enter a term in Description search or Vendor search and run that search. Each search examines only its labeled field.\n4. Review the transaction details, download results and check supporting evidence.')
        st.caption('Searches match literal text anywhere in the field, regardless of capitalization. Keyword matches may be legitimate, and nonmatches may still require review. Suggestions are not exhaustive.')
    category = st.selectbox('Prohibited-purchase category', list(CATEGORIES))
    st.write('Suggested terms: ' + ' · '.join(CATEGORIES[category]))
    description, vendor = st.columns(2)
    with description:
        with st.form('description_form'):
            st.markdown('#### Description search')
            desc = st.text_input('Keyword in transaction description', max_chars=150, placeholder='e.g. alcohol, gift card, membership')
            desc_go = st.form_submit_button('Search description', type='primary')
    with vendor:
        with st.form('vendor_form'):
            st.markdown('#### Vendor search')
            vend = st.text_input('Keyword in vendor name', max_chars=150, placeholder='e.g. USPS, post office, liquor')
            vend_go = st.form_submit_button('Search vendor', type='primary')
    if desc_go or vend_go:
        field, keyword = ('Description', desc.strip()) if desc_go else ('Vendor', vend.strip())
        if keyword:
            search({'operation':'transactions', 'filters':[{'field':field, 'keyword':keyword}]}, 'dashboard', year)
        else:
            st.session_state.pop('dashboard_result', None)
            st.session_state.pop('dashboard_csv', None)
            st.error('Enter a keyword first.')
    show_results('dashboard')

st.caption('Evidence first. Professional judgment always.')
