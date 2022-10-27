PURGE_CMD=requre-patch purge --replaces :milestone_url:str:SomeText --replaces :latency:float:0 test_data/*/*.yaml
PYTEST=python3 -m pytest -vvv -ra --showlocals

data_remove_polarion:
	rm -rf polarion/test_data

regenerate_polarion: data_remove_polarion
	# pack binary data for polarion tests
	cd polarion; $(PYTEST) export.py
	cd polarion; $(PURGE_CMD)
	cd polarion/test_data/export/; tar cfJ binary_data.tar.xz *.bin.*; rm *.bin.*

