import streamlit as st
import modules.static_eval.static_modules.code_quality as code_quality
import modules.static_eval.static_modules.syntax_structure as syntax_structure
import modules.loading.dataset_loader as dataset_loader
import modules.loading.patch_loader as patch_loader
import json
import os
import stat
import shutil


# ==================== HELPER FUNCTIONS ====================

def handle_remove_readonly(func, path, exc):
    """Error handler for removing read-only Git files on Windows"""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def cleanup_repository(repo_path):
    """
    Completely remove a repository directory.
    Handles Windows read-only Git files.
    """
    if repo_path and os.path.exists(repo_path):
        try:
            shutil.rmtree(repo_path, onerror=handle_remove_readonly)
            return True
        except Exception as e:
            st.error(f"Failed to cleanup repository: {str(e)}")
            return False
    return True


# ==================== STREAMLIT CONFIG ====================

st.set_page_config(page_title="Static Verifier", layout="wide")

st.title("Static Verifier")
st.markdown("Perform comprehensive static analysis on LLM-generated patches using configurable code quality and syntax structure analyzers.")

st.divider()


# ==================== SESSION STATE INITIALIZATION ====================

if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'repo_path' not in st.session_state:
    st.session_state.repo_path = None
if 'patch_text' not in st.session_state:
    st.session_state.patch_text = None


# ==================== STEP 1: Data Source Selection ====================

st.header("📥 Step 1: Select Data Source")

source_type = st.radio(
    "Choose your patch source:",
    ["Load from SWE-Bench Dataset", "Paste Custom Patch"],
    horizontal=True
)

if source_type == "Load from SWE-Bench Dataset":
    with st.expander("🗂️ Dataset Configuration", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            dataset_source = st.text_input(
                "Dataset Source", 
                value="princeton-nlp/SWE-bench_Verified",
                help="HuggingFace dataset ID or local JSON path"
            )
            repo_filter = st.text_input(
                "Repository Filter (Optional)", 
                value="",
                placeholder="e.g., django/django"
            )
        
        with col2:
            is_hf = st.checkbox("Load from HuggingFace", value=True)
            num_samples = st.number_input(
                "Number of Samples", 
                min_value=1, 
                max_value=10, 
                value=1
            )
    
    if st.button("🔄 Load Dataset Sample", type="primary", use_container_width=True):
        with st.spinner("Loading dataset..."):
            try:
                loader = dataset_loader.DatasetLoader(
                    source=dataset_source, 
                    hf_mode=is_hf, 
                    split="test"
                )
                
                samples = []
                for sample in loader.iter_samples(
                    limit=num_samples, 
                    filter_repo=repo_filter if repo_filter else None
                ):
                    samples.append(sample)
                
                if samples:
                    st.session_state.samples = samples
                    st.success(f"✅ Loaded {len(samples)} sample(s)")
                else:
                    st.warning("No samples found matching the criteria")
            except Exception as e:
                st.error(f"❌ Error loading dataset: {str(e)}")
    
    # Display loaded samples
    if 'samples' in st.session_state and st.session_state.samples:
        st.subheader("📋 Loaded Samples")
        
        for idx, sample in enumerate(st.session_state.samples):
            with st.expander(f"Sample {idx + 1}: {sample['repo']}", expanded=(idx == 0)):
                st.markdown(f"**Repository:** `{sample['repo']}`")
                st.markdown(f"**Base Commit:** `{sample['base_commit'][:8]}...`")
                
                if sample.get('problem_statement'):
                    st.markdown("**Problem Statement:**")
                    st.info(sample['problem_statement'][:300] + "..." if len(sample['problem_statement']) > 300 else sample['problem_statement'])
                
                st.markdown("**Patch:**")
                st.code(sample['patch'], language="diff")
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button(f"📍 Select This Sample", key=f"select_{idx}"):
                        st.session_state.selected_sample = sample
                        st.session_state.patch_text = sample['patch']
                        st.rerun()

else:  # Custom Patch
    with st.expander("✏️ Custom Patch Input", expanded=True):
        st.session_state.patch_text = st.text_area(
            "Paste your unified diff patch here:",
            value=st.session_state.patch_text or "",
            height=300,
            placeholder="""diff --git a/file.py b/file.py
index 1234567..abcdefg 100644
--- a/file.py
+++ b/file.py
@@ -10,7 +10,7 @@ def example():
-    old_code()
+    new_code()
"""
        )
        
        repo_path_input = st.text_input(
            "Repository Path (for local analysis)",
            value="",
            placeholder="C:/path/to/your/repo or leave empty to clone"
        )

st.divider()


# ==================== STEP 2: Analysis Configuration ====================

st.header("⚙️ Step 2: Configure Analysis Tools")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Code Quality Analyzers")
    
    use_pylint = st.checkbox(
        "Pylint", 
        value=True,
        help="Comprehensive code quality checker (scoring 0-10)"
    )
    
    use_flake8 = st.checkbox(
        "Flake8", 
        value=True,
        help="PEP8 style guide enforcement"
    )
    
    use_radon = st.checkbox(
        "Radon", 
        value=True,
        help="Cyclomatic complexity and maintainability index"
    )
    
    use_mypy = st.checkbox(
        "Mypy", 
        value=True,
        help="Static type checking"
    )
    
    use_bandit = st.checkbox(
        "Bandit", 
        value=True,
        help="Security vulnerability scanner"
    )

with col2:
    st.subheader("Tool Weights for SQI")
    st.caption("Adjust the importance of each tool (auto-normalized)")
    
    weight_pylint = st.slider(
        "Pylint Weight", 
        0.0, 1.0, 0.5, 0.05,
        disabled=not use_pylint
    )
    
    weight_flake8 = st.slider(
        "Flake8 Weight", 
        0.0, 1.0, 0.15, 0.05,
        disabled=not use_flake8
    )
    
    weight_radon = st.slider(
        "Radon Weight", 
        0.0, 1.0, 0.25, 0.05,
        disabled=not use_radon
    )
    
    weight_mypy = st.slider(
        "Mypy Weight", 
        0.0, 1.0, 0.05, 0.05,
        disabled=not use_mypy
    )
    
    weight_bandit = st.slider(
        "Bandit Weight", 
        0.0, 1.0, 0.05, 0.05,
        disabled=not use_bandit
    )

# Syntax structure is always enabled
st.info("ℹ️ **Syntax & Structure Analysis** is always enabled and runs independently of code quality tools.")

st.divider()


# ==================== STEP 3: Run Analysis ====================

st.header("🚀 Step 3: Run Static Analysis")

# Prepare configuration
analysis_config = {
    "checks": {
        "pylint": use_pylint,
        "flake8": use_flake8,
        "radon": use_radon,
        "mypy": use_mypy,
        "bandit": use_bandit,
    },
    "weights": {
        "pylint": weight_pylint,
        "flake8": weight_flake8,
        "radon": weight_radon,
        "mypy": weight_mypy,
        "bandit": weight_bandit,
    }
}

# Check if we have a patch to analyze
can_analyze = False
if source_type == "Load from SWE-Bench Dataset":
    can_analyze = 'selected_sample' in st.session_state
else:
    can_analyze = bool(st.session_state.patch_text)

if not can_analyze:
    st.warning("⚠️ Please select a sample or paste a custom patch to continue.")
else:
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col2:
        if st.button("▶️ Run Analysis", type="primary", use_container_width=True):
            # Handle repository setup
            repo_path = None
            
            if source_type == "Load from SWE-Bench Dataset":
                sample = st.session_state.selected_sample
                
                # Define repository path (MOVED OUTSIDE ONEDRIVE!)
                repo_base = "../modules/loading/data/repos_temp"
                repo_name = sample['repo'].replace('/', '__')
                repo_path = os.path.join(repo_base, repo_name)
                
                # Clean up existing repository if present
                if os.path.exists(repo_path):
                    with st.spinner("🧹 Removing previous repository..."):
                        if not cleanup_repository(repo_path):
                            st.stop()
                        st.success("✅ Previous repository removed")
                
                # Clone and apply patch
                with st.spinner("🔄 Cloning repository and applying patch..."):
                    try:
                        patcher = patch_loader.PatchLoader(
                            sample=sample,
                            repos_root=repo_base
                        )
                        
                        repo_path = patcher.clone_repository()
                        result = patcher.apply_patch()
                        
                        if result["applied"]:
                            st.success(f"✅ Patch applied to: {repo_path}")
                        else:
                            st.error(f"❌ Patch application failed: {result['log']}")
                            st.stop()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        st.stop()
            else:
                # Custom patch mode
                if repo_path_input:
                    repo_path = repo_path_input
                else:
                    st.error("❌ Please provide a repository path for custom patches")
                    st.stop()
            
            # Run analyses
            with st.spinner("🔍 Running static analysis..."):
                try:
                    # Code Quality Analysis
                    cq_results = code_quality.analyze(
                        repo_path=str(repo_path),
                        patch_str=str(st.session_state.patch_text),
                        config=analysis_config
                    )
                    
                    # Syntax & Structure Analysis
                    ss_results = syntax_structure.run_syntax_structure_analysis(
                        repo_path=str(repo_path),
                        diff_text=str(st.session_state.patch_text)
                    )
                    
                    st.session_state.analysis_results = {
                        "code_quality": cq_results,
                        "syntax_structure": ss_results,
                        "repo_path": str(repo_path)
                    }
                    
                    st.success("✅ Analysis complete!")
                    
                except Exception as e:
                    st.error(f"❌ Analysis failed: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())


# ==================== STEP 4: Display Results ====================

if st.session_state.analysis_results:
    st.divider()
    st.header("📊 Analysis Results")
    
    results = st.session_state.analysis_results
    cq = results["code_quality"]
    ss = results["syntax_structure"]
    
    # ===== SQI Overview =====
    if "sqi" in cq:
        sqi_data = cq["sqi"]
        
        st.subheader("🎯 Static Quality Index (SQI)")
        
        # Display SQI score prominently
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Overall SQI", 
                f"{sqi_data['SQI']}/100",
                delta=sqi_data['classification']
            )
        
        with col2:
            st.metric("Modified Files", cq['meta']['n_files'])
        
        with col3:
            st.metric("Total LOC", cq['meta']['total_loc'])
        
        with col4:
            # Color-code classification
            classification = sqi_data['classification']
            if classification == "Excellent":
                st.success(f"✅ {classification}")
            elif classification == "Good":
                st.info(f"👍 {classification}")
            elif classification == "Fair":
                st.warning(f"⚠️ {classification}")
            else:
                st.error(f"❌ {classification}")
        
        # Component breakdown
        st.markdown("**Component Scores:**")
        cols = st.columns(len(sqi_data['components']))
        
        for idx, (tool, score) in enumerate(sqi_data['components'].items()):
            with cols[idx]:
                st.metric(tool.capitalize(), f"{score}/100")
    
    st.divider()
    
    # ===== Detailed Results Tabs =====
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📝 Syntax & Structure",
        "🔧 Pylint",
        "📏 Flake8", 
        "📊 Radon",
        "🔤 Mypy",
        "🔒 Bandit",
        "💾 Raw Data"
    ])
    
    # Tab 1: Syntax & Structure
    with tab1:
        st.subheader("Syntax & Structure Analysis")
        
        for file_report in ss:
            with st.expander(f"📄 {file_report.get('path', 'Unknown')}", expanded=True):
                if file_report.get('is_code_valid'):
                    st.success("✅ Valid Python syntax")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Functions", file_report.get('n_functions', 0))
                    with col2:
                        st.metric("Classes", file_report.get('n_classes', 0))
                    with col3:
                        st.metric("AST Depth", file_report.get('ast_depth', 0))
                    
                    st.metric("Avg Function Length", f"{file_report.get('avg_func_length', 0):.1f} lines")
                    
                    if file_report.get('changed_functions'):
                        st.markdown("**Changed Functions:**")
                        st.code(", ".join(file_report['changed_functions']))
                    
                    if 'ast_diff_ratio' in file_report:
                        st.metric("Structure Change Ratio", f"{file_report['ast_diff_ratio']:.1%}")
                else:
                    st.error(f"❌ Syntax Error: {file_report.get('error', 'Unknown error')}")
                    if file_report.get('context'):
                        st.code("\n".join(file_report['context']))
    
    # Tab 2: Pylint
    with tab2:
        if cq.get('pylint'):
            st.subheader("Pylint Analysis")
            
            for file_path, issues in cq['pylint'].items():
                with st.expander(f"📄 {file_path}", expanded=len(issues) > 0):
                    if issues:
                        df_data = []
                        for issue in issues:
                            df_data.append({
                                "Line": issue.get('line', 'N/A'),
                                "Type": issue.get('type', 'N/A'),
                                "Symbol": issue.get('symbol', 'N/A'),
                                "Message": issue.get('message', 'N/A')
                            })
                        
                        st.dataframe(df_data, use_container_width=True)
                    else:
                        st.success("✅ No issues found")
        else:
            st.info("Pylint analysis was not enabled")
    
    # Tab 3: Flake8
    with tab3:
        if cq.get('flake8'):
            st.subheader("Flake8 Analysis")
            
            if cq['flake8']:
                df_data = []
                for issue in cq['flake8']:
                    df_data.append({
                        "Line": issue.get('line', 'N/A'),
                        "Code": issue.get('code', 'N/A'),
                        "Message": issue.get('message', 'N/A')
                    })
                
                st.dataframe(df_data, use_container_width=True)
            else:
                st.success("✅ No style issues found")
        else:
            st.info("Flake8 analysis was not enabled")
    
    # Tab 4: Radon
    with tab4:
        if cq.get('radon'):
            st.subheader("Radon Complexity Analysis")
            
            st.metric("Average Maintainability Index", f"{cq['radon'].get('mi_avg', 0):.2f}")
            
            if cq['radon'].get('complexity'):
                for file_path, complexities in cq['radon']['complexity'].items():
                    with st.expander(f"📄 {file_path}", expanded=True):
                        if complexities:
                            df_data = []
                            for func in complexities:
                                df_data.append({
                                    "Function": func.get('name', 'N/A'),
                                    "Complexity": func.get('complexity', 0),
                                    "Line": func.get('lineno', 'N/A')
                                })
                            
                            st.dataframe(df_data, use_container_width=True)
                        else:
                            st.info("No functions analyzed")
        else:
            st.info("Radon analysis was not enabled")
    
    # Tab 5: Mypy
    with tab5:
      if cq.get('mypy') is not None:  
        st.subheader("Mypy Type Checking")
        
        mypy_data = cq['mypy']
        
        # Check if mypy_data is a list (new detailed format) or dict (old format)
        if isinstance(mypy_data, list):
            # New detailed format - show as DataFrame
            if len(mypy_data) == 0:
                st.success("✅ No type errors found")
            else:
                # Summary metrics
                error_count = len([issue for issue in mypy_data if issue.get('severity') == 'error'])
                warning_count = len([issue for issue in mypy_data if issue.get('severity') == 'warning'])
                note_count = len([issue for issue in mypy_data if issue.get('severity') == 'note'])
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Issues", len(mypy_data))
                with col2:
                    st.metric("Errors", error_count)
                with col3:
                    st.metric("Warnings", warning_count)
                with col4:
                    st.metric("Notes", note_count)
                
                st.divider()
                
                # Convert to DataFrame
                st.markdown("**Type Checking Issues:**")
                
                df_data = []
                for issue in mypy_data:
                    # Build location string
                    location = f"{issue.get('line_number', 'N/A')}"
                    if issue.get('column'):
                        location += f":{issue.get('column')}"
                    
                    # Map severity to emoji for visual clarity
                    severity = issue.get('severity', 'error')
                    if severity == 'error':
                        severity_display = "🔴 Error"
                    elif severity == 'warning':
                        severity_display = "🟡 Warning"
                    else:
                        severity_display = "ℹ️ Note"
                    
                    df_data.append({
                        "Severity": severity_display,
                        "File": issue.get('filename', 'Unknown').split('\\')[-1],  # Just filename
                        "Location": location,
                        "Error Code": issue.get('error_code', 'N/A'),
                        "Message": issue.get('message', 'No description available')
                    })
                
                # Display DataFrame with custom styling
                st.dataframe(
                    df_data,
                    use_container_width=True,
                    height=min(400, len(df_data) * 35 + 38)  # Dynamic height, max 400px
                )
                
                # Add filter options
                with st.expander("🔍 Filter Options"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        severity_filter = st.multiselect(
                            "Filter by Severity",
                            options=["🔴 Error", "🟡 Warning", "ℹ️ Note"],
                            default=["🔴 Error", "🟡 Warning", "ℹ️ Note"]
                        )
                    
                    with col2:
                        # Get unique files
                        unique_files = list(set([issue.get('filename', 'Unknown').split('\\')[-1] for issue in mypy_data]))
                        file_filter = st.multiselect(
                            "Filter by File",
                            options=unique_files,
                            default=unique_files
                        )
                    
                    # Apply filters if any are selected
                    if severity_filter or file_filter:
                        filtered_data = [
                            row for row in df_data 
                            if row["Severity"] in severity_filter and row["File"] in file_filter
                        ]
                        
                        if filtered_data:
                            st.markdown("**Filtered Results:**")
                            st.dataframe(
                                filtered_data,
                                use_container_width=True,
                                height=min(400, len(filtered_data) * 35 + 38)
                            )
                        else:
                            st.info("No issues match the selected filters")
        
        elif isinstance(mypy_data, dict):
            # Old format - just error count (backward compatibility)
            error_count = mypy_data.get('error_count', 0)
            
            if error_count > 0:
                st.warning(f"⚠️ Found {error_count} type error(s)")
            else:
                st.success("✅ No type errors found")
        
        else:
            st.error("❌ Mypy results format not recognized")
      else:
        st.info("Mypy analysis was not enabled")
    
    # Tab 6: Bandit
    with tab6:
      if cq.get('bandit') is not None:
        st.subheader("Bandit Security Analysis")
        
        bandit_data = cq['bandit']
        
        # Check if bandit_data is a list (new detailed format) or dict (old format)
        if isinstance(bandit_data, list):
            # New detailed format - show individual issues
            if len(bandit_data) == 0:
                st.success("✅ No security issues detected")
            else:
                # Summary metrics
                severity_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
                for issue in bandit_data:
                    severity = issue.get('issue_severity', 'MEDIUM').upper()
                    severity_counts[severity] = severity_counts.get(severity, 0) + 1
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Issues", len(bandit_data))
                with col2:
                    st.metric("High Severity", severity_counts.get('HIGH', 0))
                with col3:
                    st.metric("Medium Severity", severity_counts.get('MEDIUM', 0))
                with col4:
                    st.metric("Low Severity", severity_counts.get('LOW', 0))
                
                st.divider()
                
                # Display detailed issues
                st.markdown("**Detailed Security Issues:**")
                
                for idx, issue in enumerate(bandit_data, 1):
                    severity = issue.get('issue_severity', 'MEDIUM').upper()
                    confidence = issue.get('issue_confidence', 'MEDIUM').upper()
                    
                    # Color-code by severity
                    if severity == 'HIGH':
                        severity_emoji = "🔴"
                        expanded = True
                    elif severity == 'MEDIUM':
                        severity_emoji = "🟡"
                        expanded = False
                    else:
                        severity_emoji = "🟢"
                        expanded = False
                    
                    with st.expander(
                        f"{severity_emoji} Issue #{idx}: {issue.get('test_name', 'Unknown')} - "
                        f"{issue.get('filename', 'Unknown file')}:{issue.get('line_number', '?')}",
                        expanded=expanded
                    ):
                        # Issue metadata
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.markdown(f"**Severity:** {severity}")
                        with col2:
                            st.markdown(f"**Confidence:** {confidence}")
                        with col3:
                            st.markdown(f"**Test ID:** {issue.get('test_id', 'N/A')}")
                        
                        # Location
                        st.markdown(f"**File:** `{issue.get('filename', 'Unknown')}`")
                        st.markdown(f"**Line:** {issue.get('line_number', 'N/A')}")
                        if issue.get('line_range'):
                            st.markdown(f"**Line Range:** {issue['line_range']}")
                        
                        # Issue description
                        st.markdown("**Issue:**")
                        st.warning(issue.get('issue_text', 'No description available'))
                        
                        # Code snippet
                        if issue.get('code'):
                            st.markdown("**Vulnerable Code:**")
                            st.code(issue['code'], language="python")
                        
                        # CWE reference if available
                        if issue.get('issue_cwe'):
                            cwe_info = issue['issue_cwe']
                            if isinstance(cwe_info, dict):
                                cwe_id = cwe_info.get('id', 'Unknown')
                                cwe_link = cwe_info.get('link', '#')
                                cwe_name = cwe_info.get('name', 'Unknown')
                                st.markdown(f"**CWE:** [{cwe_id}]({cwe_link})")
                    
        
        elif isinstance(bandit_data, dict):
            # Old format - just severity counts (backward compatibility)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("High Severity", bandit_data.get('HIGH', 0), 
                         delta="Critical" if bandit_data.get('HIGH', 0) > 0 else None)
            with col2:
                st.metric("Medium Severity", bandit_data.get('MEDIUM', 0))
            with col3:
                st.metric("Low Severity", bandit_data.get('LOW', 0))
            
            total_issues = sum(bandit_data.values())
            if total_issues == 0:
                st.success("✅ No security issues detected")
            else:
                st.warning(f"⚠️ Total: {total_issues} security issue(s)")
        
        else:
            st.error("❌ Bandit results format not recognized")
      else:
        st.info("Bandit analysis was not enabled")
    
    # Tab 7: Raw Data
    with tab7:
        st.subheader("Raw JSON Output")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Code Quality Results:**")
            st.json(cq)
        
        with col2:
            st.markdown("**Syntax & Structure Results:**")
            st.json(ss)
        
        # Download button
        combined_results = {
            "code_quality": cq,
            "syntax_structure": ss
        }
        
        st.download_button(
            "📥 Download Results (JSON)",
            data=json.dumps(combined_results, indent=2),
            file_name="static_analysis_results.json",
            mime="application/json"
        )
