# T-cc-daniel-board Put the Tier A/B and field models on the model board
Paths: test_models/boardExport/, DOCS/coord/handoff/*-cc-daniel-board-headline.md
Depends on: T-cc-daniel-8 (variations and ownModels outputs on main)
Done when: test_models/boardExport/out/ holds board_backtest.csv, board_forecast.csv, board_models.json and board_field.csv rebuilt by export.py, the export's self-check passes, and a handoff note tells cc-raz how to set the headline models (A-G9, B-S6)
Status: done
