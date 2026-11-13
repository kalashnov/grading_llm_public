#!/bin/bash

export SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export S="$SCRIPT_DIR/submissions"

# VA
python3 "$SCRIPT_DIR/post_grades.py" "$S/VA_8068292_q2.1_70296511_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VA_8068292_q2.2_70296512_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VA_8068292_q2.4_70296514_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VA_8068292_q2.5_70296515_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VA_8068292_q2.6_3424_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VA_8068292_q2.6_70296516_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VA_8068292_q3.1_70296521_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VA_8068292_q3.3_70296523_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VA_8068292_q3.4_70296524_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VA_8068292_q3.5_70296525_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VA_8068292_q4.1_70296527_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VA_8068292_q4.2_70296528_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VA_8068292_q4.3_70296529_requests.json" && sleep 3

# VB
python3 "$SCRIPT_DIR/post_grades.py" "$S/VB_8068374_q2.1_70296602_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VB_8068374_q2.2_70296603_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VB_8068374_q2.4_70296605_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VB_8068374_q2.5_70296606_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VB_8068374_q2.6_70296607_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VB_8068374_q3.1_70296612_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VB_8068374_q3.3_70296614_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VB_8068374_q3.4_70296615_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VB_8068374_q3.5_70296616_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VB_8068374_q4.1_70296618_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VB_8068374_q4.2_70296619_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VB_8068374_q4.3_70296620_requests.json" && sleep 3

# VC
python3 "$SCRIPT_DIR/post_grades.py" "$S/VC_8068382_q2.1_70296667_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VC_8068382_q2.2_70296668_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VC_8068382_q2.4_70296670_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VC_8068382_q2.5_70296671_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VC_8068382_q2.6_70296672_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VC_8068382_q3.1_70296677_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VC_8068382_q3.3_70296679_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VC_8068382_q3.4_70296680_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VC_8068382_q3.5_70296681_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VC_8068382_q4.1_70296683_requests.json" && sleep 3

# VC new
python3 "$SCRIPT_DIR/post_grades.py" "$S/VC_8068382_q4.2_70296684_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VC_8068382_q4.3_70296685_requests.json" && sleep 3

# VD
python3 "$SCRIPT_DIR/post_grades.py" "$S/VD_8068383_q2.1_70296696_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VD_8068383_q2.2_70296697_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VD_8068383_q2.4_70296699_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VD_8068383_q2.5_70296700_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VD_8068383_q2.6_70296701_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VD_8068383_q3.1_70296706_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VD_8068383_q3.3_70296708_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VD_8068383_q3.4_70296709_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VD_8068383_q3.5_70296710_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VD_8068383_q4.1_70296712_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VD_8068383_q4.2_70296713_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VD_8068383_q4.3_70296714_requests.json"

# 1c (q2.3) — all variants
python3 "$SCRIPT_DIR/post_grades.py" "$S/VA_8068292_q2.3_70296513_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VB_8068374_q2.3_70296604_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VC_8068382_q2.3_70296669_requests.json" && sleep 3
python3 "$SCRIPT_DIR/post_grades.py" "$S/VD_8068383_q2.3_70296698_requests.json" && sleep 3

# 1d (q2.4) — VA only
python3 "$SCRIPT_DIR/post_grades.py" "$S/VA_8068292_q2.4_70296514_requests.json"
