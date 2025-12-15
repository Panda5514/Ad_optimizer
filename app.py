import streamlit as st
from logic import generate_step1, generate_locations # Ensure these match your file
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("bria_api")

st.set_page_config(page_title="Ad Optimizer", layout="wide")

if "step" not in st.session_state: st.session_state.step = 1
if "matrix_data" not in st.session_state: st.session_state.matrix_data = None
if "winner" not in st.session_state: st.session_state.winner = None

st.title("Ad Optimizer: Global Campaign Controller")

# =========================================================
# STEP 1: ASSET DEFINITION
# =========================================================
if st.session_state.step == 1:
    st.subheader("1. Define Product & Design")
    
    # --- BOX 1 & 2: DUAL INPUT ---
    c1, c2 = st.columns(2)
    with c1:
        product_prompt = st.text_area(" The Product", "A white sneaker with black stripes", height=100)
    with c2:
        context_prompt = st.text_area(" Ad Design / Context", "A person running with a dog on a leash", height=100)

    st.divider()
    
    # --- SOURCE SELECTION ---
    st.write("###  Design Intelligence Source")
    source_mode = st.radio("How should we determine the Style?", 
        [" Reference Image (Style Clone)", " AI Matrix (Explore 9 Styles)", " Manual Control"], 
        horizontal=True
    )
    
    ref_file = None
    light_opts = []
    angle_opts = []
    
    if "Reference Image" in source_mode:
        st.info("Upload an image (e.g., from Pinterest/Instagram). We will extract its lighting, angle, and vibe.")
        ref_file = st.file_uploader("Upload Inspiration", type=["jpg", "png", "jpeg"])
        
    elif "AI Matrix" in source_mode:
        st.info("AI will generate 9 variations to help you find the perfect look.")
        c_opt1, c_opt2 = st.columns(2)
        with c_opt1:
            light_opts = st.multiselect("Lighting", ["studio_softbox", "neon_cyberpunk", "natural_sunlight", "Backlighting"], default=["studio_softbox", "neon_cyberpunk", "natural_sunlight"])
        with c_opt2:
            angle_opts = st.multiselect("Angles", ["eye_level", "low_angle", "top_down"], default=["eye_level", "low_angle", "top_down"])
            
    else: # Manual
        c_man1, c_man2 = st.columns(2)
        with c_man1: light_opts = [st.selectbox("Lighting", ["studio_softbox", "neon_cyberpunk", "natural_sunlight"])]
        with c_man2: angle_opts = [st.selectbox("Angle", ["eye_level", "low_angle", "top_down"])]

    # --- GENERATE ---
    if st.button("Generate Candidate(s)", type="primary"):
        if "Reference" in source_mode and not ref_file:
            st.error("Please upload an image!")
        else:
            with st.spinner("Analyzing & Generating..."):
                # We pass 'ref_file' to the logic. If it's None, logic ignores it.
                data, seed = generate_step1(API_KEY, product_prompt, context_prompt, light_opts, angle_opts, ref_image=ref_file)
                st.session_state.matrix_data = data
                st.session_state.master_seed = seed
                st.rerun()

    # --- DISPLAY RESULTS ---
    if st.session_state.matrix_data:
        st.divider()
        st.write("### Select the Winning Look")
        for row in st.session_state.matrix_data:
            cols = st.columns(len(row))
            for idx, item in enumerate(row):
                with cols[idx]:
                    st.image(item["url"], caption=item["label"], use_container_width=True)
                    if st.button("🏆 Select Winner", key=f"btn_{item['label']}"):
                        st.session_state.winner = item
                        st.session_state.step = 2
                        st.rerun()

# =========================================================
# STEP 2: GLOBAL DEPLOYMENT (UNCHANGED)
# =========================================================
elif st.session_state.step == 2:
    st.subheader("2. Global Deployment Instructions")
    
    col_l, col_r = st.columns([1, 2])
    
    with col_l:
        st.image(st.session_state.winner["url"], caption="Winning Asset Base")
        st.caption("This visual DNA (Lighting/Angle/Seed) will be preserved.")
        if st.button("⬅️ Back"):
            st.session_state.step = 1
            st.rerun()

    with col_r:
        st.write("### Target Markets")
        selected_locs = st.multiselect("Select Countries", ["Tokyo, Japan", "Paris, France", "New York, USA", "Mars Colony"], default=["Tokyo, Japan", "Paris, France"])
        
        # --- DYNAMIC INSTRUCTION INPUTS ---
        loc_config = {}
        if selected_locs:
            st.write("###  Special Instructions per Region")
            for loc in selected_locs:
                with st.expander(f"Instructions for {loc}", expanded=True):
                    # Pre-fill Japan example to hint the user
                    placeholder = "e.g. Make it Anime style" if "Japan" in loc else "e.g. Add cherry blossoms"
                    instruction = st.text_input(f"Directives for {loc}", placeholder=placeholder, key=f"in_{loc}")
                    loc_config[loc] = instruction
        
        if st.button("🚀 Launch Global Campaign"):
            with st.spinner("Injecting regional parameters..."):
                results = generate_locations(
                    API_KEY, 
                    st.session_state.winner["structure"], 
                    st.session_state.master_seed, 
                    loc_config
                )
                st.session_state.final_results = results
                st.session_state.step = 3
                st.rerun()

# =========================================================
# STEP 3: FINAL RESULTS
# =========================================================
elif st.session_state.step == 3:
    st.subheader("3. Campaign Output")
    st.success("✅ Generation Complete")
    
    cols = st.columns(len(st.session_state.final_results))
    for idx, res in enumerate(st.session_state.final_results):
        with cols[idx]:
            st.image(res["url"], use_container_width=True)
            st.markdown(f"**{res['loc']}**")
            if res['instruction']:
                st.caption(f"🔧 Directive: *{res['instruction']}*")
    
    if st.button("🔄 Start Over"):
        st.session_state.step = 1
        st.session_state.matrix_data = None
        st.rerun()
