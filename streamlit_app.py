"""Streamlit Community Cloud entry point. Run: streamlit run streamlit_app.py"""
import csv
import io
import os
import sqlite3
import time

import streamlit as st

from app import CATEGORIES, FIELDS, gemini_plan, run_plan
from hosted_database import DataSourceError, get_database


st.set_page_config(page_title='OSU · P-card Audit', page_icon='🔎', layout='wide')

# Keep the audit surface consistent even if the host's theme file was omitted.
st.markdown('''<style>
.stApp {background:#f4f5f1;color:#172a29;color-scheme:light;}
[data-testid="stHeader"] {background:#f4f5f1;}
[data-testid="stMainBlockContainer"] {max-width:1400px;padding-top:2rem;}
.audit-header {background:#173b35;color:white;padding:22px 28px;border-radius:8px;display:flex;align-items:center;gap:14px;margin-bottom:24px;}
.audit-logo {background:#f18b55;color:#173b35;font:bold 30px Georgia;padding:0 14px;border-radius:5px;}
.audit-brand {font-weight:700;font-size:20px;}.audit-brand small {display:block;color:#cfddd5;font-size:11px;letter-spacing:.12em;}
.audit-eyebrow {color:#b64818;font-size:12px;font-weight:700;letter-spacing:.12em;margin-bottom:8px;}
.audit-title {font:normal 44px/1.15 Georgia,serif;color:#172a29;margin:8px 0 16px;}
.audit-copy {color:#60706c;font-size:16px;margin-bottom:16px;}
.stApp [data-testid="stMarkdownContainer"], .stApp label, .stApp h1, .stApp h2, .stApp h3 {color:#172a29;}
.stApp [data-testid="stCaptionContainer"] {color:#60706c;}
.stApp [data-testid="stForm"] {background:white;border:1px solid #dce1da;border-radius:10px;padding:26px;}
.stApp [data-testid="stMetric"] {background:white;border:1px solid #dce1da;border-radius:8px;padding:18px;}
.stApp [data-testid="stMetricValue"], .stApp [data-testid="stMetricLabel"] {color:#172a29;}
.stApp input, .stApp textarea {background:white!important;color:#172a29!important;caret-color:#172a29;}
.stApp [data-baseweb="select"]>div {background:white;color:#172a29;border-color:#aebbb3;}
.stApp [data-baseweb="tab-list"] {gap:24px;background:transparent;border-bottom:1px solid #bac6bd;}
.stApp [data-baseweb="tab"] {color:#60706c;padding:16px 4px;font-size:16px;}
.stApp [data-baseweb="tab"][aria-selected="true"] {color:#172a29;font-weight:650;}
.stApp [data-baseweb="tab-highlight"] {background:#b64818;}
.stApp button[kind="primaryFormSubmit"], .stApp button[kind="primary"] {background:#b64818;color:white;border-color:#b64818;}
.stApp button[kind="primaryFormSubmit"] p, .stApp button[kind="primary"] p {color:white;}
.stApp button[kind="secondary"], .stApp button[kind="secondaryFormSubmit"] {background:white;color:#172a29;border-color:#acb9af;}
.stApp [data-testid="stExpander"] {background:#eaf0e6;border-color:#dce1da;border-radius:8px;}
.stApp [data-testid="stExpander"] details summary {color:#172a29;}
.stApp [data-testid="stAlert"] {color:#172a29;}
.audit-footer {border-top:1px solid #dce1da;color:#60706c;font-size:13px;padding-top:20px;margin-top:30px;}
@media(max-width:600px){.audit-title{font-size:34px}.audit-header{padding:18px}.stApp [data-baseweb="tab-list"]{gap:12px}.stApp [data-baseweb="tab"]{font-size:14px}}
</style>''', unsafe_allow_html=True)

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


def search(plan, target, year, page=1):
    st.session_state.pop(target + '_result', None)
    st.session_state.pop(target + '_csv', None)
    if not st.session_state.get('audit_database'):
        st.error('Searches will be available once the database connection is restored.')
        return
    try:
        with st.spinner('Searching OSU transactions…'):
            result = run_plan(plan, year, page=page, database_path=st.session_state.audit_database.path)
        st.session_state[target + '_result'] = result
    except ValueError as error:
        st.error(str(error))
    except sqlite3.Error:
        st.error('The database could not be queried. Try a narrower search or contact the website owner.')


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


st.markdown('<div class="audit-header"><span class="audit-logo">P</span><div class="audit-brand">P-card audit<small>OKLAHOMA STATE UNIVERSITY</small></div></div>', unsafe_allow_html=True)
title_column, year_column = st.columns([4, 1])
with title_column:
    st.markdown('<div class="audit-eyebrow">PURCHASING CARD REVIEW</div><h1 class="audit-title">Follow the transaction.</h1><p class="audit-copy">Search potential control deviations. Examine the evidence.</p>', unsafe_allow_html=True)

database = None
connection_error = None
try:
    with st.spinner('Connecting to the audit database…'):
        database = get_database()
except DataSourceError as error:
    connection_error = str(error)

if st.session_state.get('audit_database') is not database:
    clear_results()
    st.session_state.pop('audit_year', None)
    st.session_state.audit_database = database

with year_column:
    years = database.years if database else []
    year = st.selectbox('Calendar year', years, index=years.index(2014) if 2014 in years else 0 if years else None,
                        key='audit_year', on_change=clear_results, disabled=database is None,
                        placeholder='Database unavailable')
    st.caption('Based on transaction date')

if connection_error:
    st.warning('The database is currently unavailable. Both audit tools are shown below; searches will become available when the connection is restored.')
    with st.expander('Connection details'):
        st.error(connection_error)
        if st.button('Retry connection'):
            st.rerun()

dashboard, questions = st.tabs(['01 · Prohibited purchases', '02 · Ask the database'])

with questions:
    st.subheader('Ask a question. Inspect the evidence.')
    st.write('Ask for transaction lists, counts, totals, or spending grouped by vendor, cardholder, merchant category or month. The selected calendar year always applies.')
    st.caption('Examples: “Show transactions with alcohol in the description” · “Show total spending by vendor” · “Show transactions with amounts of at least $5,000”')
    with st.form('question_form'):
        question = st.text_area('Your question', max_chars=1000, placeholder='Show transactions with alcohol in the description')
        asked = st.form_submit_button('Ask the database', type='primary', disabled=database is None)
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
    with st.expander('How to use this dashboard', expanded=False):
        st.write('1. Select a calendar year at the top-right.\n2. Choose a policy category to see suggested keywords.\n3. Enter a term in Description search or Vendor search and run that search. Each search examines only its labeled field.\n4. Review the transaction details, download results and check supporting evidence.')
        st.caption('Searches match literal text anywhere in the field, regardless of capitalization. Keyword matches may be legitimate, and nonmatches may still require review. Suggestions are not exhaustive.')
    policy_column, search_column = st.columns([1, 2.5])
    with policy_column:
        st.markdown('<div class="audit-eyebrow">POLICY REFERENCE</div>', unsafe_allow_html=True)
        st.subheader('Prohibited purchases')
        category = st.selectbox('Prohibited-purchase category', list(CATEGORIES))
        st.caption('Suggested search terms')
        st.write(' · '.join(CATEGORIES[category]))
        st.caption('Enter a suggested term in either search field, then choose the search to run.')
    with search_column:
        with st.form('description_form'):
            st.markdown('<div class="audit-eyebrow">DESCRIPTION SEARCH · 01</div>', unsafe_allow_html=True)
            st.subheader('What was purchased?')
            desc = st.text_input('Keyword in transaction description', max_chars=150, placeholder='e.g. alcohol, gift card, membership')
            desc_go = st.form_submit_button('Search description', type='primary', disabled=database is None)
        with st.form('vendor_form'):
            st.markdown('<div class="audit-eyebrow">VENDOR SEARCH · 02</div>', unsafe_allow_html=True)
            st.subheader('Who was paid?')
            vend = st.text_input('Keyword in vendor name', max_chars=150, placeholder='e.g. USPS, post office, liquor')
            vend_go = st.form_submit_button('Search vendor', type='primary', disabled=database is None)
    if desc_go or vend_go:
        field, keyword = ('Description', desc.strip()) if desc_go else ('Vendor', vend.strip())
        if keyword:
            search({'operation':'transactions', 'filters':[{'field':field, 'keyword':keyword}]}, 'dashboard', year)
        else:
            st.session_state.pop('dashboard_result', None)
            st.session_state.pop('dashboard_csv', None)
            st.error('Enter a keyword first.')
    show_results('dashboard')

st.markdown('<div class="audit-footer">OSU P-card audit workspace · Evidence first. Professional judgment always.</div>', unsafe_allow_html=True)
