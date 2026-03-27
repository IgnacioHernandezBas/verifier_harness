import streamlit as st
import modules.loading.dataset_loader as dataset_loader
import modules.loading.patch_loader as patch_loader

st.title("SWE Bench Data Loader Patcher")
st.markdown("This page allows you to download the environments and a patches from the [SWE Bench repository](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified)")

st.header("Load Patch Dataset")

if 'load_dataset_clicked' not in st.session_state:
    st.session_state.load_dataset_clicked = False

def click_dataset_button():
    st.session_state.load_dataset_clicked = True


swe_dataset = st.text_input("Enter Dataset Source", value="princeton-nlp/SWE-bench_Verified")
especify_repo=st.text_input("Specify Repository Filter (Optional)", value="")
col1, col2,=st.columns(2)
with col1:
  is_hf=st.checkbox("Load from HuggingFace", value=True)
with col2:
  number_of_samples=st.number_input("Number of Samples to Load", min_value=1, max_value=100, value=1)
loader=dataset_loader.DatasetLoader(source=swe_dataset, hf_mode=is_hf, split="test")

button_col1, button_col2,button_col3=st.columns(3)

with button_col2:
    st.button("Load Dataset",use_container_width=True,on_click=click_dataset_button)

with st.container():
  if st.session_state.load_dataset_clicked:
      with st.spinner("Loading Dataset..."):
        counter=0
        for sample in loader.iter_samples(limit=number_of_samples, filter_repo=especify_repo if especify_repo else None):
          counter+=1
          st.subheader("Repository: {}".format(sample["repo"]))
          st.markdown("**Patch:**")
          st.code(sample["patch"], language="diff")
          st.markdown("---")
          if st.button("Apply this patch",use_container_width=True, key=sample["repo"]+"_"+str(counter)):
            with st.spinner("Cloning repository and applying patch..."):
              try:
                patch_loader_instance = patch_loader.PatchLoader(sample=sample, repos_root="C:/Users/Usuario/OneDrive/Escritorio/verifier_harness/streamlit/modules/loading/data/repos_temp")
                repo_path = patch_loader_instance.clone_repository()
                applied_info = patch_loader_instance.apply_patch()
                if applied_info["applied"]:
                  st.success("Patch applied successfully to repository at: {}".format(repo_path))
                else:
                  st.error("Failed to apply patch. Log: {}".format(applied_info["log"]))
              except Exception as e:
                st.error("An error occurred: {}".format(str(e)))
                continue