"""
TdlpackIO is a pure Python implementation for performing IO with TDLPACK sequential files
(i.e. Fortran unformatted files).  Instead of using Fortran for perform IO, we are using
Python builtins.open() in binary mode.  This allows us to perform stream-based IO for TDLPACK
files.  When a file is opened for reading, its contents (TDLPACK records) are automatically
indexed and stored in a dictionary.  The dictionary stores the byte offset the data record;
the size of the data record; date and lead time; and MOS-2000 ID.

This indexing allow the user to access a TDLPACK sequential file in a random-access nature.
For example if a users wants to read the 500th record in the file, the first 499 records in
their entirety do not need to be read.
"""
import logging
import numpy as np
import pdb
import pytdlpack
import struct
import sys  
import warnings

__version__ = pytdlpack.__version__ # Share the version number

_IS_PYTHON3 = sys.version_info.major >= 3

if _IS_PYTHON3:
    import builtins
else:
    import __builtin__ as builtins

ONE_MB = 1024 ** 3

class open(object):
    def __init__(self,filename,mode='r'):
        """
        Class Constructor

        Parameters
        ----------

        **`filename : str`**

        File name.

        **`mode : str, optional, default = 'r'`**

        File handle mode.  The default is open for reading ('r').
        """
        if mode == 'r' or mode == 'w':
            mode = mode+'b'
        elif mode == 'a':
            mode = 'wb'
        self._fh = builtins.open(filename,mode=mode,buffering=ONE_MB)
        self._hasindex = False
        self._index = {}
        self.records = 0
        self.recordnumber = 0
        # Perform indexing on read
        if 'r' in mode:
            self._get_index()

    def __enter__(self):
        """
        """
        return self

    def __exit__(self,atype,value,traceback):
        """
        """
        self.close()

    def __iter__(self):
        """
        """
        return self

    def __next__(self):
        """
        """
        if self.recordnumber < self.records:
            return self.read(1)[0]
        else:
            raise StopIteration

    def _get_index(self):
        """
        Perform indexing of data records.
        """
        #pdb.set_trace()
        # Initialize index dictionary
        self._index['offset'] = []
        self._index['size'] = []
        self._index['type'] = []
        self._index['date'] = []
        self._index['lead'] = []
        self._index['id1'] = []
        self._index['id2'] = []
        self._index['id3'] = []
        self._index['id4'] = []
        self._index['linked_station_id_record'] = []
        _last_station_id_record = 0

        # Iterate
        while True:
            try:
                # First read 4-byte Fortran record header, then read the next
                # 44 bytes which provides enough information to catalog the
                # data record.
                pos = self._fh.tell()
                fortran_header = struct.unpack('>i',self._fh.read(4))[0]
                if fortran_header >= 44:
                    bytes_to_read = 44
                else:
                    bytes_to_read = fortran_header
                temp = np.frombuffer(self._fh.read(bytes_to_read),dtype='>i4')
                _header = struct.unpack('>4s',temp[2])[0].decode()

                # Check to first 4 bytes of the data record to determine the data
                # record type.
                if _header == 'PLDT':
                    # TDLPACK data record
                    self._index['size'].append(temp[1])
                    self._index['type'].append('data')
                    self._index['date'].append(temp[6])
                    self._index['lead'].append(int(str(temp[9])[-3:]))
                    self._index['id1'].append(temp[7])
                    self._index['id2'].append(temp[8])
                    self._index['id3'].append(temp[9])
                    self._index['id4'].append(temp[10])
                    self._index['linked_station_id_record'].append(_last_station_id_record)
                else:
                    if temp[1] == 24 and temp[6] == 9999:
                        # Trailer record
                        self._index['size'].append(temp[1])
                        self._index['type'].append('trailer')
                        self._index['date'].append(None)
                        self._index['lead'].append(None)
                        self._index['id1'].append(None)
                        self._index['id2'].append(None)
                        self._index['id3'].append(None)
                        self._index['id4'].append(None)
                        self._index['linked_station_id_record'].append(_last_station_id_record)
                    else:
                        # Station ID record
                        self._index['size'].append(temp[1])
                        self._index['type'].append('station')
                        self._index['date'].append(None)
                        self._index['lead'].append(None)
                        self._index['id1'].append(400001000)
                        self._index['id2'].append(0)  
                        self._index['id3'].append(0)
                        self._index['id4'].append(0)
                        self._index['linked_station_id_record'].append(_last_station_id_record)

                # At this point we have successfully identified a TDLPACK record from
                # the file. Increment self.records and position the file pointer to
                # now read the Fortran trailer.
                self.records += 1 # Includes trailer records
                self._fh.seek(fortran_header-bytes_to_read,1)
                fortran_trailer = struct.unpack('>i',self._fh.read(4))[0]

                # Check Fortran header and trailer for the record.
                if fortran_header != fortran_trailer:
                    raise IOError('Bad Fortran record.')

                # NOTE: The 'offset' key contains the byte position in the file of where
                # data record begins. A value of 12 is added to consider a 4-byte Fortran
                # header, 4-byte "trash", and 4-byte ioctet value (already) stored on index.
                self._index['offset'].append(pos+12) # 4-byte header + 4-byte trash + 4-byte ioctet

                # Hold the record number of the last station ID record
                if self._index['type'][-1] == 'station':
                    _last_station_id_record = self.records # This should be OK.

            except(struct.error):
                self._fh.seek(0)
                break

        self._hasindex = True
        self.dates = tuple(sorted(set(self._index['date'])))
        self.leadtimes = tuple(sorted(set(self._index['lead'])))

    def close(self):
        """
        Close the file handle
        """
        self._fh.close()

    def read(self,num=None,unpack=True):
        """
        Read num records from the current position.
        """
        #pdb.set_trace()
        recs = []
        if num == 0:
            return recs
        elif num == 1:
            reclist = [self.recordnumber+1]
        elif num > 1:
            reclist = list(range(self.recordnumber+1,self.recordnumber+1+num))
        for n in reclist:
            nn = n-1 # Use this for the self._index referencing
            kwargs = {}
            self.seek(n)
            kwargs['ioctet'] = self._index['size'][nn]
            kwargs['ipack'] = np.frombuffer(self._fh.read(self._index['size'][nn]),dtype='>i4')
            if self._index['type'][nn] == 'data':
                kwargs['reference_date'] = self._index['date'][nn]
                rec = pytdlpack.TdlpackRecord(**kwargs)
                if unpack: rec.unpack()
                recs.append(rec)
            elif self._index['type'][nn] == 'station':
                kwargs['ipack'] = kwargs['ipack'].byteswap()
                rec = pytdlpack.TdlpackStationRecord(**kwargs)
                if unpack: rec.unpack()
                recs.append(rec)
            elif self._index['type'][nn] == 'trailer':
                recs.append(pytdlpack.TdlpackTrailerRecord(**kwargs))
            self.recordnumber = n
        return recs
    
    def record(self,rec,unpack=True):
        """
        Read the N-th record.
        """
        #pdb.set_trace()
        if rec is None:
            return None
        if rec <= 0:
            warnings.warn("Record numbers begin at 1.") 
            return None
        elif rec > self.records:
            warnings.warn("Not that many records in the file.")
            return None
        else:
            self.seek(rec) # Use the actual record number here.
            return self.read(1,unpack=unpack)[0]

    def seek(self,offset):
        """
        Set the position within the file in units of data records.
        """
        #pdb.set_trace()
        if self._hasindex:
            if offset == 0:
                self._fh.seek(self._index['offset'][offset])
                self.recordnumber = offset
            elif offset > 0:
                self._fh.seek(self._index['offset'][offset-1])
                self.recordnumber = offset-1
    
    def fetch(self,date=None,id=None,lead=None,unpack=True):
        """
        Fetch TDLPACK data record by means of date, lead time, id or any combination
        thereof.
        """
        #pdb.set_trace()
        recs = []
        idx = None
        match_count = 0

        # Perform matching by determining list index values for each list criteria
        # in the file index dictionary.  These index values are catted together
        # throughout the matching.
        if date is not None:
            # Match by date (i.e. reference date)
            match_count += 1
            idx = np.where(np.array(self._index['date'])==date)[0]

        if id is not None:
            # Test for type
            if type(id) is str:
                # Need all 4 words for now....
                id = [int(i) for i in list(filter(None,id.split(' ')))]
                print(id)
            # Match by MOS ID (all 4 words)
            match_count += 4
            allrecs = np.arange(self.records)
            # ID1
            if id[0] == -1:
                idx1 = allrecs
            elif id[0] >= 0:
                idx1 = np.where(np.array(self._index['id1'])==id[0])[0]
            # ID2
            if id[1] == -1:
                idx2 = allrecs
            elif id[1] >= 0:
                idx2 = np.where(np.array(self._index['id2'])==id[1])[0]
            # ID3
            if id[2] == -1:
                idx3 = allrecs
            elif id[2] >= 0:
                idx3 = np.where(np.array(self._index['id3'])==id[2])[0]
            # ID4
            if id[3] == -1:
                idx4 = allrecs
            elif id[3] >= 0:
                idx4 = np.where(np.array(self._index['id4'])==id[3])[0]

            if idx is not None:
                idx = np.concatenate((idx,idx1,idx2,idx3,idx4))
            else:
                idx = np.concatenate((idx1,idx2,idx3,idx4))

        if lead is not None:
            # Match by lead time
            match_count += 1
            if idx is not None:
                idx = np.concatenate((idx,np.where(np.array(self._index['lead'])==lead)[0]))
            else:
                #idx = np.concatenate((np.where(np.array(self._index['lead'])==lead)[0]))
                idx = np.where(np.array(self._index['lead'])==lead)[0]

        # Now determine the count of unique index values.  The count needs to match the
        # value of match_count.  Where this occurs, the index values are extracted.
        vals,cnts = np.unique(idx,return_counts=True)
        idx = vals[np.where(cnts==match_count)[0]]

        # Now we iterate over the matching index values and build the list of
        # records.
        for i in idx:
            recs.append(self.record(i+1,unpack=unpack))
        return recs
    
    def tell(self):
        """
        Return the position in units of records.
        """
        return self.recordnumber
