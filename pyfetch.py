#!/usr/bin/env python

from SOAPpy import WSDL, Types
from SOAPpy.Types import *
import serial

class RR(dict):
    def __init__(self, username, password):
        self.wsdl_file = 'rr.wsdl'
        self.auth_info = { 'appKey'   : '48566289',
                           'username' : username,
                           'password' : password,
                           'version'  : '3',
                           'style'    : 'rpc',
                 }
        self.verbose = 1

    def connect_to_wsdl(self):
        self.wsdl = WSDL.Proxy(self.wsdl_file)

    def show_wsdl_info(self):
        print len(self.wsdl.methods)
        print self.wsdl.methods.keys()
        self.wsdl.show_methods()

    def get_country_list():
        results = self.wsdl.getCountryList();
        if self.verbose:
            for country in results:
                print country

        return results

    def get_trs_details(self, sid):
        trs = self.wsdl.getTrsDetails( sid, self.auth_info )
        trs = simplify(trs)
        if self.verbose >= 2:
            for k, v in trs.iteritems():
                print "%s = %s" % ( k, v )
        return trs

    def get_trs_talkgroup_cats(self, sid):
        cats = self.wsdl.getTrsTalkgroupCats( sid, self.auth_info )
        cats = simplify(cats)
        if self.verbose >= 2:
            for cat in cats:
                print '%s: %s' % ( cat['tgCid'], cat['tgCname'] )
        return cats

    def get_trs_talkgroups(self, sid='', Cid='', Tag='', Dec=''):
        talkgroup = self.wsdl.getTrsTalkgroups( sid, Cid, Tag, Dec, self.auth_info )
        talkgroup = simplify(talkgroup)
        if self.verbose >= 2:
            for cat in talkgroup:
                print cat
        return talkgroup

    def pritty_print_trs(self, sid):
        for cat in self.get_trs_talkgroup_cats(sid):
            for talkgroup in self.get_trs_talkgroups(sid, cat['tgCid']):
                pass
            

    

class Scanner(dict):
    def __init__(self):
        self.verbose = 2

    def connect(self):
        self.device = serial.Serial('/dev/ttyS0', 38400, timeout=2)
        self.device.open()
        if self.verbose >= 2:
            print self.device

    def raw_command(self, command):
        if self.verbose >= 2:
            print "calling: " + command
        self.device.write(command + '\r')
        line = self.device.readline()
        if self.verbose >= 2:
            print "got: " + line
        return line[0:-1]

    def close(self):
        self.device.close()

    def dump_to_yaml(self, filename):
        import yaml

        config = []
        for bank_id in range(1,11):
            bank = {}
            bank['bank'] = bank_id
            bank['label'] = self.get_bank_tag(bank_id)
            bank['scanlists'] = []
            for scanlist_id in range(1,11):
                scanlist = {}
                scanlist['label'] = self.get_scanlist_tag(bank_id, scanlist_id)
                scanlist['talkgroups'] = []
                for talkgroup_id in range(1,11):
                    talkgroup = {}
                    talkgroup['label']     = self.get_talkgroup_tag(bank_id, scanlist_id, talkgroup_id)
                    talkgroup['talkgroup'] = self.get_talkgroup(bank_id, scanlist_id, talkgroup_id)
                    scanlist['talkgroups'].append( talkgroup )
                bank['scanlists'].append(scanlist)
            config.append(bank)

        stream = file(filename, 'w')
        yaml.dump(config, stream)

    def mode(self):
        modeline = self.raw_command('MD')
        return modeline

    def number_to_letter(self, number):
        if number == 1:
            return 'A'
        elif number == 2:
            return 'B'
        elif number == 3:
            return 'C'
        elif number == 4:
            return 'D'
        elif number == 5:
            return 'E'
        elif number == 6:
            return 'F'
        elif number == 7:
            return 'G'
        elif number == 8:
            return 'H'
        elif number == 9:
            return 'I'
        elif number == 10:
            return 'J'
        else:
            raise RuntimeError('unable to convert %s to a letter' % ( number ) )

    def afs_to_dec(self, afs):
        match = re.search("(\d\d)-(\d\d)(\d)", afs)
        if match:
            return int(match.group(1))*128 + int(match.group(2))*8 + int(match.group(3), 8)
        else:
            return None

    def bank_tag(bankid):
        """this method should be overridden"""
        raise NotImplementedError('bank_tag method not implemented')


class BC296D(Scanner):
    def get_bank_tag(self, bank_id):
        bankline = self.raw_command('TA B ' + self.number_to_letter(bank_id))
        match = re.search("TA\sB\s\w\s([\w\s]+)", bankline)
        if match is not None:
            if match.group(1):
                return match.group(1)
            else:
                return None
        else:
            return None

    def set_bank_tag(self, bank_id, bank_tag):
        bank_tag = bank_tag[0:15].strip()
        ok = self.raw_command('TA B %s %s' % ( self.number_to_letter(bank_id), bank_tag) )
        if ok != 'OK':
            raise EnvironmentError('unable to set_bank_tag')
        new_bank_tag = self.get_bank_tag(bank_id)
        if new_bank_tag != bank_tag:
            if self.verbose >= 2:
                print 'old: %s, new: %s' % (bank_tag, new_bank_tag)
            raise EnvironmentError('unable to set_bank_tag')
        return new_bank_tag

    def get_scanlist_tag(self, bank_id, scanlist_id):
        scanlistline = self.raw_command('TA L %s %s' % ( self.number_to_letter(bank_id),
                                                         self.number_to_letter(scanlist_id) ) )
        match = re.search("TA\sL\s\w\s\w\s([\w\s]+)", scanlistline)
        if match is not None:
            if match.group(1):
                return match.group(1)
            else:
                return None
        else:
            return None

    def set_scanlist_tag(self, bank_id, scanlist_id, scanlist_tag):
        scanlist_tag = scanlist_tag[0:15].strip()
        ok = self.raw_command('TA L %s %s %s' % ( self.number_to_letter(bank_id),
                                                  self.number_to_letter(scanlist_id),
                                                  scanlist_tag) )
        if ok != 'OK':
            raise EnvironmentError('unable to set_scanlist_tag')
        new_scanlist_tag = self.get_scanlist_tag(bank_id, scanlist_id)
        if new_scanlist_tag != scanlist_tag:
            if self.verbose >= 2:
                print 'old: %s, new: %s' % (scanlist_tag, new_scanlist_tag)
            raise EnvironmentError('unable to set_scanlist_tag')
        return new_scanlist_tag

    def get_talkgroup(self, bank_id, scanlist_id, talkgroup_position):
        talkgroup = self.raw_command('TG %s %s%s' % ( self.number_to_letter(bank_id),
                                                      scanlist_id,
                                                      talkgroup_position) )
        match = re.search("TG\s\w\s\w\d\s(.+)", talkgroup)
        if match is not None:
            if match.group(1):
                return match.group(1)
            else:
                return None
        else:
            return None

    def set_talkgroup(self, bank_id, scanlist_id, talkgroup):
        if self.verbose >= 1:
            print 'setting talkgroup "%s" on scanlist: %s' % ( talkgroup, scanlist_id )
        ok = self.raw_command('TG %s %s %s' % ( self.number_to_letter(bank_id),
                                                 scanlist_id,
                                                 talkgroup) )
        if ok != 'OK':
            raise EnvironmentError('unable to set_talkgroup')
        new_talkgroup = self.get_talkgroup(bank_id, scanlist_id)
        if scanner.afs_to_dec(new_talkgroup) != talkgroup:
            if self.verbose >= 2:
                print 'old: %s, new: %s' % (talkgroup, scanner.afs_to_dec(new_talkgroup))
            raise EnvironmentError('unable to set_talkgroup')
        return new_talkgroup


    def get_talkgroup_tag(self, bank_id, scanlist_id, talkgroup_id):
        talkgroupline = self.raw_command('TA I %s %s%s' % ( self.number_to_letter(bank_id),
                                                            self.number_to_letter( scanlist_id ),
                                                            talkgroup_id ) )
        match = re.search("TA\sI\s\w\s\w\d\s(.+)", talkgroupline)
        if match is not None:
            if match.group(1):
                return match.group(1)
            else:
                return None
        else:
            return None

    def set_talkgroup_tag(self, bank_id, scanlist_id, talkgroup_id, talkgroup_tag):
        talkgroup_tag = talkgroup_tag[0:15].strip()
        if self.verbose >= 1:
            print 'setting talkgroup tag "%s" on scanlist: %s, talkgroup: %s' % ( talkgroup_tag, scanlist_id, talkgroup_id )
        ok = self.raw_command('TA I %s %s%s %s' % ( self.number_to_letter(bank_id),
                                                    scanlist_id,
                                                    talkgroup_id,
                                                    talkgroup_tag) )
        if ok != 'OK':
            raise EnvironmentError('unable to set_talkgroup_tag')
        new_talkgroup_tag = self.get_talkgroup_tag(bank_id, scanlist_id, talkgroup_id)
        if new_talkgroup_tag != talkgroup_tag:
            if self.verbose >= 2:
                print 'old: %s, new: %s' % (talkgroup_tag, new_talkgroup_tag)
            raise EnvironmentError('unable to set_talkgroup_tag')
        return new_talkgroup_tag



class Sprogeny(dict):
    def __init__(self, scanner, rr):
        self.scanner = scanner
        self.rr = rr
        self.verbose = 1

    def populate_bank_from_rr(self, bank_config):
        sid = bank_config['sid']
        bank_id = bank_config['bank']

        for scanlist_counter in range( len(bank_config['id_lists']) ):
            foo = bank_config['id_lists']
            id_list = foo[scanlist_counter + 1]
            if id_list['label'] == '':
                continue
            scanner.set_scanlist_tag( bank_id, scanlist_counter, id_list['label'] )
            for talkgroup_counter in range( len(id_list['talkgroups']) ):
                bar = id_list['talkgroups']
                talkgroup = bar[talkgroup_counter+1]
                if talkgroup == '':
                    continue
                if self.verbose >= 1:
                    print "configuring talkgroup %s (%s)" % ( talkgroup, scanner.afs_to_dec(talkgroup) )
                talkgroup_list = rr.get_trs_talkgroups(sid, '', '', scanner.afs_to_dec(talkgroup))
                # It's possible that we have more than one result here.
                # There's no way to decide which we want, though.
                talkgroup = talkgroup_list.pop()
                scanner.set_talkgroup( bank_id, scanlist_counter, talkgroup_counter, talkgroup['tgDec'] )
                scanner.set_talkgroup_tag( bank_id, scanlist_id, talkgroup['tgAlpha'] )
                
            
if __name__ == '__main__':
    import sys
    import ConfigParser

    config = ConfigParser.ConfigParser()
    config.read('sprogeny.cfg')

    username = config.get('radioreference', 'username' )
    password = config.get('radioreference', 'password' )
    rr = RR( username, password )
    wsdl = rr.connect_to_wsdl()

    scanner = BC296D()
    scanner.connect()

    sprogeny = Sprogeny(scanner, rr)
    
    bank_config = { 'bank' : 1,
                    'sid'  : 366,
                    'id_lists' : [ { 'label' : 'Police Patrol',
                                     'talkgroups' : [ '10-020',
                                                      '10-021',
                                                      '10-022',
                                                      '10-023',
                                                      '10-025',
                                                      '10-026',
                                                      '10-027',
                                                      '10-030',
                                                      '',
                                                      '',
                                                      ]
                                     },
                                   { 'label' : 'Special Ops',
                                     'talkgroups' : [ '10-040',
                                                      '10-043',
                                                      '10-044',
                                                      '10-045',
                                                      '10-046',
                                                      '10-047',
                                                      '10-050',
                                                      '10-051',
                                                      '10-052',
                                                      '',
                                                      ]
                                     },
                                   { 'label' : 'TAC',
                                     'talkgroups' : [ '10-041',
                                                      '10-042',
                                                      '10-056',
                                                      '',
                                                      '',
                                                      '',
                                                      '',
                                                      '',
                                                      '',
                                                      '',
                                                      ]
                                     },
                                   { 'label' : 'Command',
                                     'talkgroups' : [ '11-000',
                                                      '11-001',
                                                      '11-002',
                                                      '11-003',
                                                      '11-004',
                                                      '11-005',
                                                      '11-006',
                                                      '11-007',
                                                      '',
                                                      '',
                                                      ]
                                     },
                                   { 'label' : 'Emergency Prep',
                                     'talkgroups' : [ '09-020',
                                                      '09-021',
                                                      '09-022',
                                                      '09-023',
                                                      '09-024',
                                                      '09-025',
                                                      '09-026',
                                                      '09-027',
                                                      '09-030',
                                                      '',
                                                      ]
                                     },
                                   { 'label' : 'Surveillance',
                                     'talkgroups' : [ '10-065',
                                                      '10-103',
                                                      '10-106',
                                                      '10-107',
                                                      '10-110',
                                                      '10-112',
                                                      '10-121',
                                                      '10-141',
                                                      '',
                                                      '',
                                                      ]
                                     },
                                   { 'label' : '',
                                     'talkgroups' : [ '',
                                                      '',
                                                      '',
                                                      '',
                                                      '',
                                                      '',
                                                      '',
                                                      '',
                                                      '',
                                                      '',
                                                      ]
                                     },
                                   { 'label' : '',
                                     'talkgroups' : [ '',
                                                      '',
                                                      '',
                                                      '',
                                                      '',
                                                      '',
                                                      '',
                                                      '',
                                                      '',
                                                      '',
                                                      ]
                                     },
                                   { 'label' : 'Fire',
                                     'talkgroups' : [ '08-020',
                                                      '08-021',
                                                      '08-022',
                                                      '08-023',
                                                      '08-030',
                                                      '09-081',
                                                      '09-082',
                                                      '09-083',
                                                      '09-084',
                                                      '09-085',
                                                      ]
                                     },
                                   { 'label' : 'Assorted',
                                     'talkgroups' : [ '08-027',  # Mutual Aid 154.2800 (fire)
                                                      '09-031',  # M.E.R.S WX 
                                                      '10-055',  # MUTUAL AID - 155.475 North Tower 
                                                      '10-057',  # MUTUAL AID - 155.475 South Tower 
                                                      '11-057',  # Claycomo Police Dispatch
                                                      '11-081',  # MO DOT KC Scout Dispatch ( Lee's Summit )
                                                      '11-082',  # MO DOT KC Scout (Car To Car) 
                                                      '09-086',  # HazMat 1 
                                                      '',  # 
                                                      '',  # 
                                                      ]
                                     },
                                   ]
                    }    

    # sprogeny.populate_bank_from_rr(bank_config)
    scanner.dump_to_yaml('scanner.yml')
