import os
import re
import configparser
import pickle
from operator import iadd, isub
from collections import OrderedDict

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

class Character:
    def __init__(self, game_class, race):
        self.item_class_map = {'consumable': 0, 'container': 1, 'weapon': 2, 'armor': 4, 'reagent': 5, 
                               'projectile': 6, 'trade good': 7, 'recipe': 9, 'quiver': 11, 'quest': 12, 
                               'key': 13, 'miscellaneous': 15}

        self.item_subclass_map = {'cloth': 1, 'leather': 2, 'mail': 3, 'plate': 4}

        self.item_quality_map = {'poor': 0, 'common': 1, 'uncommon': 2, 
                                 'rare': 3, 'epic': 4, 'legendary': 5}

        self.item_type_map = {'head': [1], 'neck': [2], 'shoulders': [3], 'chest': [4, 5, 20], 
                              'waist': [6], 'legs': [7], 'feet': [8], 'wrists': [9], 
                              'hands': [10], 'finger1': [11], 'finger2': [11], 'trinket1': [12], 
                              'trinket2': [12], 'one-hand': [13, 21], 'shield': [14], 'ranged': [15], 
                              'back': [16], 'two_hand': [17], 'offhand': [22], 'thrown': [25], 
                              'gun': [26], 'bow': [15], 'left-hand': [22], 'relic': [28]}

        self.stat_reverse_map = {1: 'health', 3: 'agility', 4: 'strenght', 
                                 5: 'intellect', 6: 'spirit', 7: 'stamina'}

        self.stat_map = {'health': 1, 'agility': 3, 'strenght': 4, 
                         'intellect': 5, 'spirit': 6, 'stamina': 7}

        self.spell_map = {'on use': 0, 'on equip': 1, 'chance on hit': 2, 
                          'soulstone': 4, 'on use without delay': 5}

        self.bounding_map = {'no binding': 0, 'bind on pickup': 1, 'bind on equip': 2, 
                             'bind on use': 3 ,'quest item': 4}
        
        self.bounding_reverse_map = {0: 'no binding', 1: 'bind on pickup', 2: 'bind on equip', 
                                     3: 'bind on use', 4: 'quest item'}

        self.damage_map = {'physical': 0, 'holy': 1, 'fire': 2, 'nature': 3, 
                           'frost': 4, 'shadow': 5, 'arcane': 6}
        
        self.damage_reverse_map = {0: 'physical', 1: 'holy', 2: 'fire', 3: 'nature', 
                                   4: 'frost', 5: 'shadow', 6: 'arcane'}
        
        self.race_map = {'human': 1, 'orc': 2, 'dwarf': 3, 'elf': 4, 
                         'undead': 5, 'tauren': 6, 'gnome': 7, 'troll': 8}

        self.class_map = {'warrior': 1, 'paladin': 2, 'hunter': 3, 'rogue': 4, 'prist': 5, 
                          'shaman': 7, 'mage': 8, 'warlock': 9, 'druid': 11}
        
        # order is matter add_remove_stats method
        self.bonus_stats = ('Increase Spell Dam', 'Increase Fire Dam', 'Increase Shadow Dam', 
                            'Increase Nature Dam', 'Increase Frost Dam', 'Increase Holy Dam', 
                            'Increase Arcane Dam', 'Increase Healing', 'Increased Critical', 
                            'Increased Critical Spell', 'Increased Mana Regen', 'Increased Defense', 
                            'Increased Dodge', 'Increased Parry', 'Attack Power', 'Increased Hit Chance')
        
        self.bonus_attr_name = ('spell_power', 'spell_fire_power', 'spell_shadow_power', 
                                'spell_nature_power', 'spell_frost_power', 'spell_holy_power', 
                                'spell_arcane_power', 'healing_power', 'base_crit', 
                                'base_spell_crit', 'mana_reg_bonus', 'defence',
                                'base_dodge', 'parry', 'base_attack_power', 'hit_chance')
        
        self.resist_type = ('holy_res', 'fire_res', 'nature_res', 
                            'frost_res', 'shadow_res', 'arcane_res')
        
        self.game_class = self.valid_key(game_class, self.class_map)
        self.race = self.valid_key(race, self.race_map)
        
        self.engine = self.connect()
        self.items = pd.read_sql_query(""" 
        SELECT 
          entry AS id, name, AllowableClass, InventoryType, subclass, Quality, bonding, 
          armor, holy_res, fire_res, nature_res, frost_res, shadow_res, arcane_res,
          stat_type1, stat_value1, 
          stat_type2, stat_value2, 
          stat_type3, stat_value3, 
          stat_type4, stat_value4,
          stat_type5, stat_value5,
          dmg_min1, dmg_max1, dmg_type1,
          dmg_min2, dmg_max2, dmg_type2,
          dmg_min3, dmg_max3, dmg_type3,
          delay,
          spelltrigger_1, s1.SpellName AS sp1, s1.EffectBasePoints1 AS spb1, 
          spelltrigger_2, s2.SpellName AS sp2, s2.EffectBasePoints1 AS spb2, 
          spelltrigger_3, s3.SpellName AS sp3, s3.EffectBasePoints1 AS spb3
        FROM item_template
          LEFT JOIN spell_template as s1 ON spellid_1 = s1.Id
          LEFT JOIN spell_template as s2 ON spellid_2 = s2.Id
          LEFT JOIN spell_template as s3 ON spellid_3 = s3.Id
        """, self.engine)
        
        self.base_hp_mana = pd.read_sql_query("""
        SELECT *
        FROM player_classlevelstats
        WHERE level = 60 and class = %(cls)s;
        """, self.engine, params={'cls': self.class_map[self.game_class]})
        
        self.base_stats = pd.read_sql_query("""
        SELECT *
        FROM player_levelstats
        WHERE level = 60 and class = %(cls)s and race = %(race)s;
        """, self.engine, params={'cls': self.class_map[self.game_class], 
                                  'race': self.race_map[self.race]})
        
        # main stats
        self.sta = self.base_stats['sta'].values[0]
        self.str = self.base_stats['str'].values[0]
        self.inte = self.base_stats['inte'].values[0]
        self.spi = self.base_stats['spi'].values[0]
        self.agi = self.base_stats['agi'].values[0]
        
        # resist
        self.holy_res = 0
        self.fire_res = 0
        
        if self.race == 'undead':
            self.shadow_res = 10
        else:
            self.shadow_res = 0
        
        if (self.race == 'tauren') or (self.race == 'elf'):
            self.nature_res = 10
        else:
            self.nature_res = 0
        
        if self.race == 'dwarf':
            self.frost_res = 10
        else:
            self.frost_res = 0
        
        if self.race == 'gnome':
            self.arcane_res = 10
        else:
            self.arcane_res = 0
        
        # base values of stats
        self.bonus_hp = 0
        self.base_armor = 0
        self.base_attack_power = 0
        self.base_spell_crit = 0
        self.base_crit = 0
        self.base_dodge = 0
        self.mana_reg_bonus = {'paladin': 15, 'hunter': 15, 'warlock': 15, 'druid': 15,
                               'prist': 12.5, 'mage': 12.5, 
                               'shaman': 17,
                               'warrior': 0, 'rogue': 0}[self.game_class]  
        
        self.hp = 0
        self.mana = 0
        self.armor = 0
        self.melee_attack_power = 0
        self.range_attack_power = 0
        self.spell_power = 0
        self.healing_power = 0
        self.crit = 0
        self.spell_crit = 0   
        self.mana_reg = 0
        self.hit_chance = 0

        if self.race == 'elf':
            self.dodge = 1
        else:
            self.dodge = 0
        self.parry = 0
        self.defence = 0
        
        self.spell_holy_power = 0
        self.spell_fire_power = 0
        self.spell_shadow_power = 0
        self.spell_nature_power = 0
        self.spell_frost_power = 0
        self.spell_arcane_power = 0
        
        self.calculate_stats()
        
        self.items_on = {item: None for item in self.item_type_map}
        
    def valid_key(self, key, mapper):
        # check if key is valid
        if key in mapper:
            return key
        else: 
            print('Valid keys are: ', mapper.keys())
            raise KeyError('Invalid key: {}'.format(key))
    
    def calculate_stats(self):
        if self.race == 'tauren':
            self.hp = self.base_hp_mana['basehp'].values[0] + self.sta * 10.5 + self.bonus_hp
        else:
            self.hp = self.base_hp_mana['basehp'].values[0] + self.sta * 10 + self.bonus_hp
        self.mana = self.base_hp_mana['basemana'].values[0] + self.inte * 15
        self.armor = self.agi * 2 + self.base_armor
        
        # melee attack power from strenght 
        if self.game_class in ['hunter', 'mage', 'prist', 'rogue', 'warlock']:
            self.melee_attack_power = self.base_attack_power + self.str
        else:
            self.melee_attack_power = self.base_attack_power + self.str * 2
        
        # range attack power from agility 
        if self.game_class in ['rogue', 'warrior']:
            self.range_attack_power = self.base_attack_power + self.agi
        elif self.game_class == 'hunter':
            self.range_attack_power = self.base_attack_power + self.agi * 2
            
        # melee attack power from agility 
        if self.game_class in ['rogue', 'druid', 'hunter']:
            self.melee_attack_power += self.agi
            
        # crit from agility
        if self.game_class in ['druid', 'paladin', 'shaman', 'warrior']:
            self.crit = self.base_crit + self.agi / 20
        elif self.game_class == 'rogue':
            self.crit = self.base_crit + self.agi / 29            
        elif self.game_class == 'hunter':
            self.crit = self.base_crit + self.agi / 53 
        else: 
            self.crit = self.base_crit
            
        # spell crit from intellect
        if self.game_class == 'paladin':
            self.spell_crit = self.base_spell_crit + self.inte / 54
        else:
            self.spell_crit = self.base_spell_crit + self.inte / 60
            
        # mana reg
        if self.game_class in ['druid', 'paladin', 'warlock', 'hunter', 'shaman']:
            self.mana_reg = self.mana_reg_bonus + self.spi / 5
        elif self.game_class in ['mage', 'prist']:
            self.mana_reg = self.mana_reg_bonus + self.spi / 4
        
        # dodge from agility
        if self.game_class == 'rogue':
            self.dodge = self.base_dodge + self.agi / 14.5            
        elif self.game_class == 'hunter':
            self.dodge = self.base_dodge + self.agi / 26
        else:
            self.dodge = self.base_dodge + self.agi / 20     
        
            
    def wear_item(self, ids):
        # check if item with such id exist
        temp = self.items.loc[self.items['id'] == ids]
        if temp.shape[0] == 0:
            raise KeyError('No item with such id.')
        
        item_type = temp['InventoryType'].values[0]
        for key, value in self.item_type_map.items():
            if item_type in value:
                slot = key
                break
        
        # if one ring is equipped check another one
        if (slot == 'finger1') and (self.items_on[slot] is not None) and (self.items_on['finger2'] is None):
            slot = 'finger2'
        elif (slot == 'finger2') and (self.items_on[slot] is not None) and (self.items_on['finger1'] is None):
            slot = 'finger1'

        # if one trinket is equipped check another one
        if (slot == 'trinket1') and (self.items_on[slot] is not None) and (self.items_on['trinket2'] is None):
            slot = 'trinket2'
        elif (slot == 'trinket2') and (self.items_on[slot] is not None) and (self.items_on['trinket1'] is None):
            slot = 'trinket1'
        
        # check if character can wear it
        if (temp['AllowableClass'].values[0] == -1) or \
        (temp['AllowableClass'].values[0] == self.class_map[self.game_class]):
            pass
        else:
            raise KeyError('Can\'t be used by your class.')
            
        # remove old item
        if self.items_on[slot] is not None:
            self.add_remove_stats('sub', self.items.loc[self.items['id'] == self.items_on[slot]])
            self.items_on[slot] = None
        
        # add stats from new item
        self.add_remove_stats('add', temp)
        
        # update dict
        self.items_on[slot] = ids
    
    def add_remove_stats(self, operation, temp):
        if operation == 'sub':
            operator = isub
        elif operation == 'add':
            operator = iadd
            
        # main stats
        for i in range(1, 6):
            stat_type = temp['stat_type{}'.format(i)].values[0]
            value = temp['stat_value{}'.format(i)].values[0]
            if stat_type == 1:
                self.bonus_hp = operator(self.bonus_hp, value)
            elif stat_type == 3:
                self.agi = operator(self.agi, value)
            elif stat_type == 4:
                self.str = operator(self.str, value)
            elif stat_type == 5:
                if self.race == 'gnome':
                    self.inte = operator(self.inte, value * 1.05)
                else:
                    self.inte = operator(self.inte, value)
            elif stat_type == 6:
                if self.race == 'human':
                    self.spi = operator(self.spi, value * 1.05)
                else:
                    self.spi = operator(self.spi, value)
            elif stat_type == 7:
                self.sta = operator(self.sta, value)  
                
        # armor
        self.base_armor = operator(self.base_armor, temp['armor'].values[0])
        
        # resist
        for resist_type in self.resist_type:
            value = temp[resist_type].values[0]
            self.__setattr__(resist_type, value if operation == 'add' else -value)
        
        # green bonuses
        for i in range(1, 4):
            bonus_type = temp['sp{}'.format(i)].values[0]
            value = temp['spb{}'.format(i)].values[0]
            # if None no need to check stats in other columns
            if bonus_type is None:
                    continue
            for bonus, stat in zip(self.bonus_stats, self.bonus_attr_name):
                # check if  within available bonuses
                if re.search('{}( \d+)?$'.format(bonus), bonus_type):
                    # if bonus has it value in the end of string
                    if re.search('{}( \d+)?$'.format(bonus), bonus_type).group(1):
                        value = int(re.search('{}( \d+)?$'.format(bonus), bonus_type).group(1).strip())
                    prev_value = self.__getattribute__(stat)
                    self.__setattr__(stat, prev_value + value if operation == 'add' 
                                     else prev_value - value)
                    break
        
        # recalculate stats
        self.calculate_stats()
    
    def remove_item(self, slot):
        slot = self.valid_key(slot, self.item_type_map)
        # old item to remove
        temp = self.items.loc[self.items['id'] == self.items_on[slot]]
        
        # update stats
        self.add_remove_stats('sub', temp)
        
        # update dict
        self.items_on[slot] = None
        
    def show_empty_slots(self):
        empty = []
        
        for key, value in self.items_on.items():
            if value is None:
                empty.append(key)
        
        return empty

    def summary(self, resist=False):
        orddict = OrderedDict()
        
        for key, value in zip(['hp', 'mana', 'mana_reg', 'stamina', 'strength', 'intellect', 'agility',
                               'spirit', 'armor', 'physical_reduction', 'melee_ap', 'range_ap', 
                               'spell_power', 'healing_power', 'crit', 'spell_crit', 'hit_chance',
                               'dodge', 'parry', 'defence'],
                              [self.hp, self.mana, self.mana_reg, self.sta, self.str, self.inte, self.agi,
                               self.spi, self.armor, self.physical_damage_reduction(), self.melee_attack_power, 
                               self.range_attack_power, self.spell_power, self.spell_holy_power, self.crit, 
                               self.spell_crit, self.hit_chance, self.dodge, self.parry, self.defence]):
            if key == 'physical_reduction':    
                orddict[key] = round(value, 3)
            else:
                orddict[key] = round(value, 1)
            
        if resist:
            for key, value in zip(['holy_res', 'fire_res', 'nature_res', 'frost_res', 'shadow_res', 'arcane_res'],
                                  [self.holy_res, self.fire_res, self.nature_res, 
                                   self.frost_res, self.shadow_res, self.arcane_res]):
                orddict[key] = value            
        
        return orddict

    def physical_damage_reduction(self, attacker_level=60):
        return self.armor / (self.armor + (467.5 * attacker_level - 22167.5))        

    def spell_resist_chance(self, school='', caster_level=60):
        if school:
            school = self.valid_key(school, self.resist_type)
            resist = self.__getattribute__(school)
        else:
            resist = max([self.holy_res, self.fire_res, self.nature_res, 
                          self.frost_res, self.shadow_res, self.arcane_res])
        return (resist / (5 * caster_level)) * 0.75
    
    def human_readable_df(self, df):
        temp = df.copy()
        columns = df.columns.to_list()
        start_stat = columns.index('stat_type1')
        bonus_stat = columns.index('spelltrigger_1')
        
        temp = temp.drop(['stat_type1', 'stat_value1', 'stat_type2', 'stat_value2', 'stat_type3', 
                          'stat_value3', 'stat_type4', 'stat_value4', 'stat_type5', 'stat_value5',
                          'dmg_min2', 'dmg_max2', 'dmg_type2', 'dmg_min3', 'dmg_max3', 'dmg_type3', 
                          'spelltrigger_1', 'sp1', 'spb1', 'spelltrigger_2', 'sp2', 'spb2', 
                          'spelltrigger_3', 'sp3', 'spb3', 
                          'AllowableClass', 'InventoryType', 'subclass', 'Quality'], axis=1)
        
        for col in ('stamina', 'strenght', 'intellect', 'agility', 'spirit', 'health') + self.bonus_stats:
            temp.loc[:, col] = 0   
            
        temp['delay'] = temp['delay'] / 1000
        temp['bonding'] = temp['bonding'].map(self.bounding_reverse_map)
        temp['dmg_type1'] = temp['dmg_type1'].map(self.damage_reverse_map)
        

        for row in df.itertuples():
            idx = row[1]
            stat_row = row[start_stat + 1: start_stat + 10 + 1]
            # main stat
            for i in range(5):
                if stat_row[2 * i] == 0:
                    continue
                temp.loc[temp['id'] == idx, self.stat_reverse_map[stat_row[2 * i]]] = stat_row[2 * i + 1]

            bonus_row = row[bonus_stat + 1: bonus_stat + 9 + 1]
            # bonus stat
            for i in range(3):
                if bonus_row[3 * i + 1] is None:
                    continue
                value = bonus_row[3 * i + 2]
                for bonus in self.bonus_stats:
                    # check if  within available bonuses
                    if re.search('{}( \d+)?$'.format(bonus), bonus_row[3 * i + 1]):
                        # if bonus has it value in the end of string
                        if re.search('{}( \d+)?$'.format(bonus), bonus_row[3 * i + 1]).group(1):
                            value = int(re.search('{}( \d+)?$'.format(bonus), 
                                                  bonus_row[3 * i + 1]).group(1).strip())
                        temp.loc[temp['id'] == idx, bonus] = value
                        break

        return temp
    
    def search(self, slot, armor_type='', quality='epic', 
               orderby=['armor'], asc=False, 
               resist=False, additional_spell_power=False):
        slot = self.valid_key(slot, self.item_type_map)
        quality = self.valid_key(quality, self.item_quality_map)
        for stat in orderby:
            if stat not in ('stamina', 'strenght', 'intellect', 'agility', 'spirit', 'health', 'armor') \
            + self.bonus_stats:
                print('Valid bonuses stats', self.bonus_stats)
                raise KeyError('Invalid bonus name: {}'.format(stat))

        # leave default value for slot that doesn't have armor_type
        if slot in ['neck', 'finger1', 'finger2', 'trinket1', 'trinket2', 'one-hand', 'shield', 'ranged', 
                    'back', 'two_hand', 'offhand', 'thrown', 'gun', 'bow', 'left-hand', 'relic']:
            armor_type = ''
            
        if armor_type:
            armor_type = self.valid_key(armor_type, self.item_subclass_map)
        
        temp = self.items.loc[((self.items['AllowableClass'] == -1) | \
                               (self.items['AllowableClass'] == self.class_map[self.game_class])) & \
                              (self.items['Quality'] == self.item_quality_map[quality]) & \
                              (self.items['InventoryType'].isin(self.item_type_map[slot])) & \
                              (self.items['subclass'] == self.item_subclass_map[armor_type] 
                               if armor_type else True), :].copy()
        
        if temp.shape[0] == 0:
            return temp
        
        temp = self.human_readable_df(temp).sort_values(orderby, ascending=asc)
        
        # to hide resist
        if not resist:
            temp = temp.drop(['holy_res', 'fire_res', 'nature_res',
                              'frost_res', 'shadow_res', 'arcane_res'], axis=1)
        
        # to hide spell power for specific schools
        if not additional_spell_power:
            temp = temp.drop(['Increase Fire Dam', 'Increase Shadow Dam', 'Increase Nature Dam', 
                              'Increase Frost Dam', 'Increase Holy Dam', 'Increase Arcane Dam'], axis=1)
        
        return temp
    
    def connect(self):
        # read config
        config = configparser.ConfigParser()
        config.read('main.ini')
        # connect to database
        engine = create_engine('mysql+pymysql://{}:{}@localhost/{}'.format(config['SQL']['username'], 
                                                                           config['SQL']['password'], 
                                                                           config['SQL']['database']))
        return engine
    
    def save(self, name, path='./characters'):
        'Save class instance and delete connection to db for security reason'
        # check if connection is established
        if 'engine' in self.__dict__:
            del self.engine
        pickle.dump(self, open(os.path.join(path, name), 'wb'))
        
    @staticmethod    
    def load(name, path='./characters'):
        'Load class instance and create new connection to database'
        inst = pickle.load(open(os.path.join(path, name), 'rb'))
        inst.engine = inst.connect()
        return inst