python -m pip install -r requirements.txt
cd extractor
rd /s /q "outputs/US/Referenced files/Mario Stadium"
python refactor_main.py
pause