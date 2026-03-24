cd /home/tuq24452/code/GUIAgent/aguvis
streamlit run streamlit_ui/app.py

ssh -J tuq24452@129.32.95.123 -p 22 tuq24452@129.32.95.51

ssh -J tuq24452@129.32.95.123 -L 8501:127.0.0.1:8501 tuq24452@129.32.95.51

ssh -J tuq24452@129.32.95.123 -L 8766:127.0.0.1:8766 tuq24452@129.32.95.51