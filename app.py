import streamlit as st
import pandas as pd
import os
from datetime import datetime
import json
import hashlib

# Configure page
st.set_page_config(
    page_title="Link Checker Tool",
    page_icon="🔗",
    layout="wide"
)

# Data storage files
DATA_FILE = "workbook_data.json"
AUTH_FILE = "admin_auth.json"

# Default admin password (you should change this)
DEFAULT_PASSWORD = "admin123"

def hash_password(password):
    """Hash password for secure storage"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    """Verify password against hash"""
    return hash_password(password) == hashed

def init_admin_auth():
    """Initialize admin authentication if not exists"""
    if not os.path.exists(AUTH_FILE):
        auth_data = {
            "password_hash": hash_password(DEFAULT_PASSWORD),
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(AUTH_FILE, 'w') as f:
            json.dump(auth_data, f)

def check_admin_auth():
    """Check if admin is authenticated"""
    return st.session_state.get('admin_authenticated', False)

def authenticate_admin(password):
    """Authenticate admin with password"""
    if os.path.exists(AUTH_FILE):
        with open(AUTH_FILE, 'r') as f:
            auth_data = json.load(f)
        return verify_password(password, auth_data['password_hash'])
    return False

def save_workbook_data(data):
    """Save workbook data to JSON file and remove old data"""
    # Remove old workbook file if exists
    if os.path.exists(DATA_FILE):
        try:
            old_data = load_workbook_data()
            if old_data and 'filename' in old_data:
                st.info(f"🗑️ Removing old workbook: {old_data['filename']}")
        except:
            pass
    
    # Save new workbook data
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

def load_workbook_data():
    """Load workbook data from JSON file"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def process_excel_file(uploaded_file):
    """Process uploaded Excel file and extract all data"""
    try:
        # Read all sheets
        excel_data = pd.read_excel(uploaded_file, sheet_name=None, engine='openpyxl')
        
        workbook_data = {
            'sheets': {},
            'upload_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'filename': uploaded_file.name,
            'file_size': uploaded_file.size
        }
        
        total_rows = 0
        for sheet_name, df in excel_data.items():
            # Convert DataFrame to list of lists for easier searching
            sheet_data = []
            for idx, row in df.iterrows():
                row_data = []
                for col in df.columns:
                    cell_value = str(row[col]) if pd.notna(row[col]) else ""
                    row_data.append(cell_value)
                sheet_data.append(row_data)
            
            workbook_data['sheets'][sheet_name] = {
                'data': sheet_data,
                'columns': list(df.columns),
                'rows': len(df)
            }
            total_rows += len(df)
        
        workbook_data['total_rows'] = total_rows
        return workbook_data
        
    except Exception as e:
        st.error(f"Error processing Excel file: {str(e)}")
        return None

def search_link_in_workbook(workbook_data, search_term):
    """Search for a link/term in the workbook data"""
    results = []
    search_term_lower = search_term.lower().strip()
    
    if not search_term_lower:
        return results
    
    for sheet_name, sheet_info in workbook_data['sheets'].items():
        sheet_data = sheet_info['data']
        columns = sheet_info['columns']
        
        for row_idx, row in enumerate(sheet_data):
            for col_idx, cell_value in enumerate(row):
                if search_term_lower in str(cell_value).lower():
                    col_name = columns[col_idx] if col_idx < len(columns) else f"Column_{col_idx + 1}"
                    results.append({
                        'sheet': sheet_name,
                        'row': row_idx + 2,  # +2 because pandas starts from 0 and Excel has header
                        'column': col_name,
                        'cell_value': str(cell_value),
                        'match_type': 'Exact' if search_term_lower == str(cell_value).lower() else 'Partial'
                    })
    
    return results

def admin_login_form():
    """Display admin login form"""
    st.subheader("🔐 Admin Authentication Required")
    st.warning("This section is password protected to prevent unauthorized workbook uploads.")
    
    with st.form("admin_login"):
        password = st.text_input("Enter Admin Password:", type="password", placeholder="Enter password")
        login_button = st.form_submit_button("🔓 Login")
        
        if login_button:
            if authenticate_admin(password):
                st.session_state['admin_authenticated'] = True
                st.success("✅ Authentication successful!")
                st.rerun()
            else:
                st.error("❌ Invalid password. Access denied.")
    
    st.info("💡 **Default password is:** `admin123` (Please change this in production)")

def admin_panel():
    """Display admin panel for authenticated users"""
    st.header("🔧 Admin Panel - Upload Latest Workbook")
    
    # Logout button
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🚪 Logout"):
            st.session_state['admin_authenticated'] = False
            st.rerun()
    
    with col1:
        st.markdown("Upload your daily workbook file here. **This will automatically replace the existing workbook.**")
    
    # Show current workbook info if exists
    current_data = load_workbook_data()
    if current_data:
        st.info(f"📋 **Current workbook:** {current_data['filename']} | "
                f"**Uploaded:** {current_data['upload_time']} | "
                f"**Size:** {current_data.get('file_size', 0):,} bytes")
    
    uploaded_file = st.file_uploader(
        "Choose Excel file (.xlsx or .xls)",
        type=['xlsx', 'xls'],
        help="Upload your Excel workbook with multiple sheets. This will replace any existing workbook."
    )
    
    if uploaded_file is not None:
        # Show file info
        st.write("**📁 File Information:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Filename", uploaded_file.name)
        with col2:
            st.metric("Size", f"{uploaded_file.size:,} bytes")
        with col3:
            st.metric("Type", uploaded_file.type)
        
        # Confirm upload button
        if st.button("🔄 **Replace Current Workbook**", type="primary"):
            with st.spinner("Processing new workbook..."):
                new_workbook_data = process_excel_file(uploaded_file)
                
                if new_workbook_data:
                    # Save the new workbook data (this automatically removes old data)
                    save_workbook_data(new_workbook_data)
                    
                    st.success("✅ **Workbook replaced successfully!**")
                    st.balloons()
                    
                    # Display new workbook info
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Sheets", len(new_workbook_data['sheets']))
                    with col2:
                        st.metric("Total Rows", f"{new_workbook_data['total_rows']:,}")
                    with col3:
                        st.metric("Upload Time", new_workbook_data['upload_time'])
                    
                    # Show sheet details
                    st.subheader("📊 New Workbook Details")
                    sheet_info = []
                    for sheet_name, sheet_data in new_workbook_data['sheets'].items():
                        sheet_info.append({
                            'Sheet Name': sheet_name,
                            'Rows': f"{sheet_data['rows']:,}",
                            'Columns': len(sheet_data['columns'])
                        })
                    
                    st.dataframe(pd.DataFrame(sheet_info), use_container_width=True)
                    
                    st.success("🎉 Users can now search in the updated workbook!")

def main():
    # Initialize admin authentication
    init_admin_auth()
    
    st.title("🔗 Link Checker Tool")
    st.markdown("---")
    
    # Create tabs for User and Admin sections
    tab1, tab2 = st.tabs(["👤 User - Check Links", "🔧 Admin - Upload Workbook"])
    
    # Load existing workbook data
    workbook_data = load_workbook_data()
    
    with tab1:
        st.header("🔍 Check if Link Exists in Workbook")
        
        if workbook_data is None:
            st.warning("⚠️ **No workbook has been uploaded yet.**")
            st.info("Please ask the admin to upload a workbook first in the Admin tab.")
            
            # Show instructions
            with st.expander("📖 How to use this tool"):
                st.markdown("""
                **For Users:**
                1. Wait for the admin to upload a workbook
                2. Paste your link/URL in the search box
                3. Get instant results showing if the link exists
                
                **For Admins:**
                1. Go to the Admin tab
                2. Enter the admin password
                3. Upload your daily Excel workbook
                4. The system will replace the old workbook automatically
                """)
            return
        
        # Display current workbook info
        st.success(f"📋 **Current workbook:** {workbook_data['filename']} | "
                  f"**Uploaded:** {workbook_data['upload_time']} | "
                  f"**Sheets:** {len(workbook_data['sheets'])} | "
                  f"**Total rows:** {workbook_data['total_rows']:,}")
        
        # Search input
        search_term = st.text_input(
            "🔗 Enter the link or URL to search for:",
            placeholder="Paste your link here (e.g., https://example.com)",
            help="Enter any link, URL, or text you want to find in the workbook"
        )
        
        if search_term:
            with st.spinner("🔍 Searching in workbook..."):
                results = search_link_in_workbook(workbook_data, search_term)
            
            if results:
                st.success(f"✅ **Found {len(results)} matches** for your search!")
                
                # Display results in a nice format
                for i, result in enumerate(results, 1):
                    with st.expander(f"Match {i}: Sheet '{result['sheet']}' - Row {result['row']} - Column '{result['column']}'"):
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.write("**📍 Location:**")
                            st.write(f"Sheet: `{result['sheet']}`")
                            st.write(f"Row: `{result['row']}`")
                            st.write(f"Column: `{result['column']}`")
                            st.write(f"Match: `{result['match_type']}`")
                        with col2:
                            st.write("**📄 Cell Content:**")
                            st.code(result['cell_value'], language=None)
                
                # Summary table
                st.subheader("📊 Search Results Summary")
                results_df = pd.DataFrame(results)
                st.dataframe(results_df, use_container_width=True)
                
                # Download results as CSV
                csv = results_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Results as CSV",
                    data=csv,
                    file_name=f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
                
            else:
                st.error("❌ **No matches found!**")
                st.info("The link you searched for was not found in any of the sheets in the current workbook.")
                
                # Show available sheets for reference
                with st.expander("📋 Available sheets in current workbook"):
                    for sheet_name, sheet_info in workbook_data['sheets'].items():
                        st.write(f"• **{sheet_name}** - {sheet_info['rows']:,} rows")

    with tab2:
        # Check if admin is authenticated
        if not check_admin_auth():
            admin_login_form()
        else:
            admin_panel()

if __name__ == "__main__":
    main()
