# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CduCreator
                                 A QGIS plugin
 This plugin creates CDU (Certificato di Destinazione Urbanistica)
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-07-18
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Gter srl
        email                : assistenzagis@gter.it
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QDir, QSize
from PyQt5.QtGui import QIcon, QPainter, QImage, QTextDocument
from PyQt5.QtWidgets import QAction, QFileDialog, QMessageBox, QProgressBar, QDialog, QCheckBox
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtXml import QDomDocument
from qgis.core import *
from qgis.core import QgsMapLayerProxyModel
from qgis.utils import *
import processing
# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .cdu_creator_dialog import CduCreatorDialog
import os.path
import os
from datetime import datetime
import webbrowser
import tempfile
import shutil
from shutil import copyfile

class CduCreator:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'CduCreator_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&CDU Creator')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        #self.first_start = None
        
        self.pluginIsActive = False
        
        #self.aoiIndex = -1
        self.foglioIndex = 0
        self.show_values = []
        self.particellaIndex = 0
        self.foglio_values = []
        self.gruppoIndex = 0
        self.out_tempdir_s = ''
        self.lyr = ''
        self.group_names = []
        self.cdu_path_folder = ''
        self.CduTitle = 'Certificato di Destinazione Urbanistica (CDU)'
        self.CduComune = ''
        self.input_logo_path = ''
        self.checkAreaBox = False
        self.root = ''
        self.input_txt_path = ''
        
        

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('CduCreator', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/cdu_creator/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Create CDU'),
            callback=self.pressIcon,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True
        print('sono in initgui')
        self.dlg = CduCreatorDialog()

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&CDU Creator'),
                action)
            self.iface.removeToolBarIcon(action)
            
    def pressIcon(self):
        if not self.pluginIsActive:
            self.pluginIsActive = True
            self.dlg = CduCreatorDialog()
            
            self.param_txt = os.path.join(self.plugin_dir, 'input.txt')
            if os.path.isfile(self.param_txt) and os.path.getsize(self.param_txt) > 0:
                param_file = open(self.param_txt, "r")
                param = param_file.readlines()
                self.cdu_path_folder = param[0].strip()
                self.CduTitle = param[1].strip()
                self.CduComune = param[2].strip()
                self.input_logo_path = param[3].strip()
                self.input_txt_path = param[4].strip()
                self.checkAreaBox = param[5].strip()
                self.dlg.OutFolder.setText(self.cdu_path_folder)
                self.dlg.titolo.setText(self.CduTitle)
                self.dlg.nomeComune.setText(self.CduComune)
                self.dlg.urlLogo.setText(self.input_logo_path)
                self.dlg.urlTxt.setText(self.input_txt_path)
                if self.checkAreaBox == 'True':
                    self.checkAreaBox = True
                    self.dlg.printAreaBox.setChecked(True)
                else:
                    self.checkAreaBox = False
                    self.dlg.printAreaBox.setChecked(False)
                param_file.close()
            else:
                param_file = open(self.param_txt, "w+")
                param_file.close()

            print(self.lyr)
            if QgsProject.instance().mapLayersByName('terreni_catastali'):
                self.lyr = QgsProject.instance().mapLayersByName('terreni_catastali')[0]
                        
                self.dlg.OutFolderButton.clicked.connect(self.exportCduButton)
                self.dlg.OutFolder.textChanged.connect(self.handleOutFolder)
                self.dlg.clearButton.clicked.connect(self.clearButton)
                self.dlg.helpButton.clicked.connect(self.openHelpButton)
                self.dlg.foglioComboBox.currentIndexChanged.connect(self.foglioBox)
                self.dlg.particellaComboBox.currentIndexChanged.connect(self.particellaBox)
                self.dlg.gruppoComboBox.currentIndexChanged.connect(self.gruppoBox)
                self.dlg.logoButton.clicked.connect(self.importLogo)
                self.dlg.urlLogo.textChanged.connect(self.handleLogo)
                self.dlg.txtButton.clicked.connect(self.importTxt)
                self.dlg.urlTxt.textChanged.connect(self.handleTxt)
                self.dlg.titolo.textChanged.connect(self.handleTitle)
                self.dlg.nomeComune.textChanged.connect(self.handleComune)
                self.dlg.printAreaBox.stateChanged.connect(self.handleAreaBox)
                self.dlg.pushButtonOk.clicked.connect(self.run)
                self.dlg.rejected.connect(self.closePlugin)
                
                self.prepRun()
                self.dlg.show()
            else:
                self.iface.messageBar().pushMessage("ATTENZIONE", "Il layer terreni_catastali non è caricato nel progetto.", level=Qgis.Critical, duration=4)
        else:
            self.dlg.show()
            self.dlg.activateWindow()
            
    def foglioBox(self, idxf):
        #print('foglio')
        #print(self.lyr)
        self.foglioIndex = idxf
        if self.foglioIndex == 0:
            self.dlg.particellaComboBox.setEnabled(False)
            uniquevalues = []
            # #print(uniquevalues)
            uniqueprovider = self.lyr.dataProvider()
            fields = uniqueprovider.fields()
            id = fields.indexFromName('FOGLIO')
            uniquevalues = list(uniqueprovider.uniqueValues( id ))
            # #print(len(uniquevalues))
            # #print(uniquevalues)
            
            self.show_values = []
            for uv in uniquevalues:
                #print (uv)
                if uv != NULL and uv != '':
                    str_value = str(uv)
                    self.show_values.append(str_value)
                # #str_values = str(uv).split("\\")
                # #if len(str_values) > 1: #per percorsi regione veneto mettere 4
                    # #show_values.append(str_values[1] + ' - ' + str_values[2]) #per percorsi regione veneto mettere 5 e 6
            #print (self.show_values)
            
            self.show_values.sort()
            self.dlg.particellaComboBox.clear()
            self.dlg.particellaComboBox.addItem('') #--> aggiunge una riga vuota nell'elenco della combo
            self.dlg.particellaComboBox.addItems(sv for sv in self.show_values)
        else:
            self.dlg.particellaComboBox.setEnabled(True)
            self.show_values = []
            filter = self.dlg.foglioComboBox.currentText()
            #print (filter)
            values = [feat['MAPPALE'] for feat in self.lyr.getFeatures() if feat['FOGLIO'] == filter]
            list_val = set(values)
            for uv in list_val:
                if uv != '':
                    self.show_values.append(uv)
            
            self.show_values.sort()
            self.dlg.particellaComboBox.clear()        
            self.dlg.particellaComboBox.addItem('') #--> aggiunge una riga vuota nell'elenco della combo
            self.dlg.particellaComboBox.addItems(sv for sv in self.show_values)
            
    def particellaBox(self, idxp):
        print('fai qualcosa')
        self.particellaIndex = idxp
        print(self.particellaIndex)
        #vlayer = self.dlg.catastoComboBox.currentLayer()
        
    def popComboFoglio(self):
        uniqueprovider = self.lyr.dataProvider()
        fields = uniqueprovider.fields()
        unique_foglio = []
        id_foglio = fields.indexFromName('FOGLIO') 
        unique_foglio = list(uniqueprovider.uniqueValues( id_foglio ))

        self.foglio_values = []
        for uv_f in unique_foglio:
            if uv_f != NULL:
                str_value_f = str(uv_f)
                self.foglio_values.append(str_value_f)
                
        self.foglio_values.sort()
        self.dlg.foglioComboBox.clear()
        self.dlg.foglioComboBox.addItem('')
        self.dlg.foglioComboBox.addItems(fv for fv in self.foglio_values)
            
    def unique(self, fi_ov): 
        # intilize a null list 
        unique_list = [] 
          
        # traverse for all elements 
        for x in fi_ov: 
            # check if exists in unique_list or not 
            if x not in unique_list: 
                unique_list.append(x) 
        # print list 
        return unique_list
        
    def gruppoBox(self, idxg):
        print('gruppo')
        self.gruppoIndex = idxg
        print(self.gruppoIndex)
        #vlayer = self.dlg.catastoComboBox.currentLayer()
        
    def exportCduButton(self):
        self.cdu_out_folder = QFileDialog.getExistingDirectory()
        self.cdu_path_folder = QDir.toNativeSeparators(self.cdu_out_folder)
        print (self.cdu_out_folder)
        print (self.cdu_path_folder)
        cdu_txt_folder = self.dlg.OutFolder.setText(self.cdu_path_folder)
        
    def handleOutFolder(self, val):
        self.cdu_path_folder = val
        print(self.cdu_path_folder)
        
    def handleTitle(self, val):
        self.CduTitle = val
        print(self.CduTitle)
        
    def handleComune(self, val):
        self.CduComune = val
        print(self.CduComune)
        
    def importLogo(self):
        self.input_logo, _filter = QFileDialog.getOpenFileName(None, "Open ", '.', "(*.png)")
        print (self.input_logo)
        self.input_logo_path = QDir.toNativeSeparators(self.input_logo)
        #print (self.input_logo)
        print (self.input_logo_path)
        input_logo_txt = self.dlg.urlLogo.setText(self.input_logo_path)
        
    def handleLogo(self, val):
        self.input_logo_path = val
        print(self.input_logo_path)
        
    def importTxt(self):
        self.input_txt, _filter = QFileDialog.getOpenFileName(None, "Open ", '.', "(*.txt)")
        print (self.input_txt)
        self.input_txt_path = QDir.toNativeSeparators(self.input_txt)
        print (self.input_txt_path)
        input_txt_txt = self.dlg.urlTxt.setText(self.input_txt_path)
        
    def handleTxt(self, val):
        self.input_txt_path = val
        print(self.input_txt_path)

    def handleAreaBox(self):
        #self.checkNegBox = state
        if self.dlg.printAreaBox.isChecked() == True:
            self.checkAreaBox = True
            print('check')
        else:
            self.checkAreaBox = False
            print('ucheck')
        
    def clearButton(self):
        self.dlg.textLog.clear()
        
    def openHelpButton(self):
        # if QgsSettings().value('locale/userLocale') == 'it':
        webbrowser.open('https://manuale-cdu-creator.readthedocs.io/it/latest/')
        # elif QgsSettings().value('locale/userLocale') == 'es':
            # webbrowser.open('https://chm-from-lidar-manuale.readthedocs.io/es/latest/')
        # else:
            # webbrowser.open('https://chm-from-lidar-manuale.readthedocs.io/en/latest/')
        
    def prepRun(self):
            
        self.popComboFoglio()
        
        self.root = QgsProject.instance().layerTreeRoot()
        #print(root.children())
        child = self.root.children()
        self.group_names = []
        for ch in child:
            if isinstance(ch, QgsLayerTreeGroup):
                print (type(ch))
                self.group_names.append(ch.name())
                
        self.dlg.gruppoComboBox.clear()
        self.dlg.gruppoComboBox.addItem('')
        self.dlg.gruppoComboBox.addItems(gro for gro in self.group_names)
        
        self.dlg.titolo.setText(self.CduTitle)
        
        
    def closePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        print("** CLOSING Plugin")

        self.dlg.OutFolderButton.clicked.disconnect(self.exportCduButton)
        self.dlg.OutFolder.textChanged.disconnect(self.handleOutFolder)
        self.dlg.clearButton.clicked.disconnect(self.clearButton)
        self.dlg.helpButton.clicked.disconnect(self.openHelpButton)
        self.dlg.foglioComboBox.currentIndexChanged.disconnect(self.foglioBox)
        self.dlg.particellaComboBox.currentIndexChanged.disconnect(self.particellaBox)
        self.dlg.gruppoComboBox.currentIndexChanged.disconnect(self.gruppoBox)
        self.dlg.logoButton.clicked.disconnect(self.importLogo)
        self.dlg.urlLogo.textChanged.disconnect(self.handleLogo)
        self.dlg.txtButton.clicked.disconnect(self.importTxt)
        self.dlg.urlTxt.textChanged.disconnect(self.handleTxt)
        self.dlg.titolo.textChanged.disconnect(self.handleTitle)
        self.dlg.nomeComune.textChanged.disconnect(self.handleComune)
        self.dlg.printAreaBox.stateChanged.disconnect(self.handleAreaBox)
        self.dlg.pushButtonOk.clicked.disconnect(self.run)
        self.dlg.rejected.disconnect(self.closePlugin)
        
        self.pluginIsActive = False
        #self.aoiIndex = -1
        self.foglioIndex = 0
        self.show_values = []
        self.particellaIndex = 0
        self.foglio_values = []
        self.gruppoIndex = 0
        self.out_tempdir_s = ''
        self.lyr = ''
        self.group_names = []
        self.cdu_path_folder = ''
        self.CduTitle = 'Certificato di Destinazione Urbanistica (CDU)'
        self.CduComune = ''
        self.input_logo_path = ''
        self.checkAreaBox = False
        self.root = ''
        self.input_txt_path = ''
        
        
        if self.out_tempdir_s != '':
            self.out_tempdir_s.cleanup()

        self.out_tempdir_s = ''

        from qgis.utils import reloadPlugin
        reloadPlugin("CduCreator")
            

    def run(self):
        self.dlg.textLog.setText(self.tr('INIZIO PROCESSO...\n'))
        QCoreApplication.processEvents()
        
        if self.gruppoIndex == 0:
            self.dlg.textLog.append(self.tr('ATTENZIONE: nessun gruppo è stato selezionato, selezionare il gruppo contenete i dati urbanistici\n'))
            return
            
        if self.cdu_path_folder == '':
            self.dlg.textLog.append(self.tr('ERRORE: nessuna cartella di output è stata selezionata\n'))
            return
            
        param_file = open(self.param_txt, "w")
        param_file.write(self.cdu_path_folder + '\n')
        param_file.write(self.CduTitle + '\n')
        param_file.write(self.CduComune + '\n')
        param_file.write(self.input_logo_path + '\n')
        param_file.write(self.input_txt_path + '\n')
        param_file.write(str(self.checkAreaBox) + '\n')
        param_file.close()

        result = True
        # See if OK was pressed
        if result:
            print('sono in run')
            if self.out_tempdir_s == '':
                self.out_tempdir_s = tempfile.TemporaryDirectory()
            else:
                self.out_tempdir_s.cleanup()
                self.out_tempdir_s = tempfile.TemporaryDirectory()
            
            out_tempdir = self.out_tempdir_s
            
            # sel_foglio = self.foglio_values[self.foglioIndex - 1]
            # print(sel_foglio)
            # sel_particella = self.show_values[self.particellaIndex - 1]
            # print(sel_particella)
            
            selectedGroupIndex = self.dlg.gruppoComboBox.currentIndex()
            print (selectedGroupIndex)
            selectedGroup = self.group_names[selectedGroupIndex - 1]
            print (selectedGroup)
            
            if self.lyr.selectedFeatureCount() > 0 and self.foglioIndex == 0 and self.particellaIndex == 0:
                selectedF = self.lyr.selectedFeatures()[0]
                sel_foglio = selectedF["FOGLIO"]
                print(sel_foglio)
                sel_particella = selectedF["MAPPALE"]
                print(sel_particella)
                if self.lyr.selectedFeatureCount() > 1:
                    self.dlg.textLog.append(self.tr('ATTENZIONE: sono state selezionate più particelle catastali, selezionare una sola particella\n'))
                    return
                else:
                    selected_feat = QgsProcessingFeatureSourceDefinition(self.lyr.id(), True)
                    print(selected_feat)
            elif self.foglioIndex != 0 and self.particellaIndex != 0:
                sel_foglio = self.foglio_values[self.foglioIndex - 1]
                #print(sel_foglio)
                sel_particella = self.show_values[self.particellaIndex - 1]
                #print(sel_particella)
                if self.lyr.selectedFeatureCount() > 0:
                    self.dlg.textLog.append(self.tr('ATTENZIONE: era già presente una selezione nel layer terreni_catastali, verrà sovrascritta con la particella foglio: {} e mappale: {}.\n'.format(sel_foglio, sel_particella)))
                    QCoreApplication.processEvents()

                self.lyr.selectByExpression("FOGLIO={} AND MAPPALE={}".format(sel_foglio, sel_particella))
                selected_feat = QgsProcessingFeatureSourceDefinition(self.lyr.id(), True)
            elif self.lyr.selectedFeatureCount() == 0 and self.foglioIndex == 0 and self.particellaIndex == 0:
                self.dlg.textLog.append(self.tr('ATTENZIONE: nessuna particella è stata selezionata, selezionare un mappale\n'))
                return
                    
            box = self.lyr.boundingBoxOfSelected()
            map = iface.mapCanvas()
            map.setExtent(box)
            map.refresh()
            
            #root = QgsProject.instance().layerTreeRoot()
            #print(root.children())
            #child = self.root.children()[0]
            #print (child0.name())

            #crea gruppo per layers temporanei
            new_group_lyr = self.root.insertGroup(0, 'temp')

            #salva la feat selezionata in uno shp, la aggiunge al gruppo e cambia lo stile (per usarla nell'img)
            processing.run("native:saveselectedfeatures", { 'INPUT' : self.lyr, 
                        'OUTPUT' : '{}/aoi.shp'.format(out_tempdir.name)})
            aoi_pathfile = os.path.join(out_tempdir.name, 'aoi.shp')
            lyr_aoi = QgsVectorLayer(aoi_pathfile, 'aoi')
            QgsProject.instance().addMapLayers([lyr_aoi], False)
            new_group_lyr.insertLayer(-1, lyr_aoi)
            aoi_symbol = QgsFillSymbol.createSimple({'border_width_map_unit_scale': '3x:0,0,0,0,0,0', 'color': '243,166,178,0', 'outline_color': '255,255,0,255', 'outline_style': 'solid', 'outline_width': '0.6', 'outline_width_unit': 'MM'})
            lyr_aoi.renderer().setSymbol(aoi_symbol)
            lyr_aoi.triggerRepaint()
            iface.layerTreeView().refreshLayerSymbology(lyr_aoi.id())
            
            #legge gruppi, sottogruppi e layers nel layer tree e aggiunge a un dizionario solo quelli che intersecano l'area di interesse
            layers = []
            layers_name = []
            subgr_name = []
            layers_dict = {}
            for child in self.root.children():
                if isinstance(child, QgsLayerTreeGroup):
                    if child.name() == selectedGroup:
                        for gr in child.children():
                            if isinstance(child, QgsLayerTreeGroup):
                            #print(gr.name())
                                subgr_name.append(gr.name())
                                lyrs = gr.findLayers()
                                for l in lyrs:
                                    #print(lyr.name())
                                    #print(lyr.layerId())
                                    processing.run("native:selectbylocation", {'INPUT': l.layer(),
                                            'PREDICATE': [0],
                                            'INTERSECT': selected_feat,
                                            'METHOD': 0})
                                    if l.layer().selectedFeatureCount() > 0:
                                        layers.append(l.layer())
                                        layers_name.append(l.name())
                                        layers_dict[layers[-1]] = (subgr_name[-1], layers_name[-1])
                                        l.layer().removeSelection()

            if len(layers) > 0:
                shp_count = 0
                pos = 0
                intersec_name = []
                print_dict = {}
                for key, value in layers_dict.items():
                    #print(key)
                    file_name = 'intersect_{}.gpkg'.format(shp_count)
                    processing.run("native:clip", {'INPUT': key,
                                        'OVERLAY': selected_feat,
                                        'OUTPUT': '{}/{}'.format(out_tempdir.name, file_name)})

                    int_lyr_pathfile = os.path.join(out_tempdir.name, file_name)
                    int_lyr_name = file_name.split('.')
                    lyr_intersect = QgsVectorLayer(int_lyr_pathfile, int_lyr_name[0])
                    QgsProject.instance().addMapLayers([lyr_intersect], False)
                    new_group_lyr.insertLayer(pos, lyr_intersect)
                    pos += 1
                    shp_count += 1
                    intersec_name.append(int_lyr_name[0])
                    layers_dict[key] = (value[0], value[1], intersec_name[-1])
                    #print(key.name())
                    #print(value[0])
                    #print(value[1])
                    #print(intersec_name[-1])
                    
                    alias = key.attributeAliases()
                    #print(key.name())
                    #print(alias)
                    descr_list = []
                    nome_list = []
                    rif_list = []
                    art_list = []
                    for keys, values in alias.items():
                        if values.casefold() == 'descrizione'.casefold() or keys.casefold() == 'descrizione'.casefold():
                            descr_list.insert(0, keys)
                            #print(descr_name)
                        else:
                            descr_list.append('descrizione')
                            #print('pippo')
                        if values.casefold() == 'nome'.casefold() or keys.casefold() == 'nome'.casefold():
                            nome_list.insert(0, keys)
                        else:
                            nome_list.append('nome')
                        if values.casefold() == 'riferimento legislativo'.casefold() or keys.casefold() == 'riferimento legislativo'.casefold():
                            rif_list.insert(0, keys)
                        else:
                            rif_list.append('riferimento legislativo')
                        if values.casefold() == 'articolo'.casefold() or keys.casefold() == 'articolo'.casefold():
                            art_list.insert(0, keys)
                        else:
                            art_list.append('articolo')
                    #print(descr_list)
                    #print(nome_list)
                    #print(rif_list)
                    #print(art_list)
                    #print(layers_dict)
                    #print(layers_dict[key][2])
                    sel_lyr_int = QgsProject.instance().mapLayersByName(layers_dict[key][2])

                    #print(sel_lyr_int[0])
                    #print(sel_lyr_int[0].name())
                    descr_index = sel_lyr_int[0].fields().indexFromName(descr_list[0])
                    #print(descr_index)
                    nome_index = sel_lyr_int[0].fields().indexFromName(nome_list[0])
                    #print(nome_index)
                    rifleg_index = sel_lyr_int[0].fields().indexFromName(rif_list[0])
                    #print(rifleg_index)
                    rifnto_index = sel_lyr_int[0].fields().indexFromName(art_list[0])
                    #print(rifnto_index)
                    for fl in sel_lyr_int[0].getFeatures():
                        unique_id = layers_dict[key][2] + '_' + str(fl.id())
                        #print(unique_id)
                        area = fl.geometry().area()
                        if descr_index != -1:
                            #print('Descrizione: {}'.format(fl["Descrizion"]))
                            descr = '- Descrizione: {}'.format(fl[descr_list[0]])
                            if fl[descr_list[0]] == NULL:
                                descr = '- Descrizione: -'
                        else:
                            descr = '- Descrizione: -'
                        sbgr_lyr = '{} - {}'.format(layers_dict[key][0], layers_dict[key][1])
                        if nome_index != -1:
                            nome = '- Nome: {}'.format(fl[nome_list[0]])
                            if fl[nome_list[0]] == NULL:
                                nome = '- Nome: -'
                        else:
                            nome = '- Nome: -'
                        if rifleg_index != -1:
                            rif_leg = '- Riferimento legislativo: {}'.format(fl[rif_list[0]])
                            if fl[rif_list[0]] == NULL:
                                rif_leg = '- Riferimento legislativo: -'
                        else:
                            rif_leg = '- Riferimento legislativo: -'
                        if rifnto_index != -1:
                            rif_nto = '- Articolo: {}'.format(fl[art_list[0]])
                            if fl[art_list[0]] == NULL:
                                rif_nto = '- Articolo: -'
                        else:
                            rif_nto = '- Articolo: -'
                        area_tot = '- Area totale (mq): {:.3f}'.format(area)
                        print_dict[unique_id] = (sbgr_lyr, nome, descr, rif_leg, rif_nto, area_tot)
                #print(print_dict)
                
                    if nome_index == -1:
                        self.dlg.textLog.append(self.tr('ATTENZIONE: la colonna "Nome" non è stata trovata nel layer {}.\n'.format(layers_dict[key][1])))
                        QCoreApplication.processEvents()
                    if descr_index == -1:
                        self.dlg.textLog.append(self.tr('ATTENZIONE: la colonna "Descrizione" non è stata trovata nel layer {}.\n'.format(layers_dict[key][1])))
                        QCoreApplication.processEvents()
                    if rifleg_index == -1:
                        self.dlg.textLog.append(self.tr('ATTENZIONE: la colonna "Riferimento legislativo" non è stata trovata nel layer {}.\n'.format(layers_dict[key][1])))
                        QCoreApplication.processEvents()
                    if rifnto_index == -1:
                        self.dlg.textLog.append(self.tr('ATTENZIONE: la colonna "Articolo" non è stata trovata nel layer {}.\n'.format(layers_dict[key][1])))
                        QCoreApplication.processEvents()

                self.lyr.removeSelection()
                
                #crea immagine della mappa centrata sull'area di interesse
                img = QImage(QSize(500, 500), QImage.Format_ARGB32_Premultiplied)

                settings = QgsMapSettings()
                img_layers = QgsProject.instance().mapLayersByName('terreni_catastali')
                img_layers2 = QgsProject.instance().mapLayersByName('aoi')
                print_layers = layers.copy()
                print_layers.insert(0, img_layers[0])
                print_layers.insert(0, img_layers2[0])
                settings.setLayers(print_layers)
                rect = QgsRectangle(box)
                rect.scale(2.5)
                settings.setExtent(rect)
                settings.setOutputSize(img.size())

                #crea la printer per stampare il pdf
                printer = QPrinter()
                printer.setPageSize(QPrinter.A4)
                #printer.setPageMargins(10, 10, 10, 10, QPrinter.Millimeter)
                printer.setFullPage(True)
                printer.setOutputFormat(QPrinter.PdfFormat)
                cdu_pdf_name = 'cdu_F{}_M{}_{}.pdf'.format(sel_foglio, sel_particella, datetime.now().strftime("%d%m%Y_%H%M%S"))
                cdu_pdf_path = os.path.join(self.cdu_path_folder, cdu_pdf_name)
                printer.setOutputFileName(cdu_pdf_path)

                #salva l'immagine della mappa come png
                pdfPainter = QPainter()
                pdfPainter.begin(img)
                render = QgsMapRendererCustomPainterJob(settings, pdfPainter)
                render.start()
                render.waitForFinished()
                pdfPainter.end()
                img_path_file = os.path.join(out_tempdir.name, 'map.png')
                img.save(img_path_file)

                #compone l'html e stampa il pdf
                stringa = '<!DOCTYPE html><html><head><style>p {font-size: 13px;}</style></head><body>'
                if self.input_logo_path != '':
                    if os.path.isfile(self.input_logo_path):
                        stringa += '<p style="text-align:center; vertical-align: middle;"><img height="60" src="' + self.input_logo_path + '"></p>'
                    else:
                        self.dlg.textLog.append(self.tr('ATTENZIONE: il file PNG {} non è stato trovato, il Logo non verrà stampato.\n'.format(self.input_logo_path)))
                        QCoreApplication.processEvents()
                stringa += '<h2 style="text-align:center">' + self.CduTitle + ' - Comune di ' + self.CduComune + '</h2>'
                stringa += '<hr><br>'
                stringa += '<p>Prot. n°<br>Lì,</p>'
                stringa += '<h3 style="text-align:center">Il Responsabile del Servizio</h3>'
                stringa += '<p>Vista la richiesta del _____________________________ presentata in data ____/____/____ prot. n. ________;<br></p>'
                if self.input_txt_path != '':
                    if os.path.isfile(self.input_txt_path):
                        txt_file = open(self.input_txt_path, "r")
                        #print(file.read())
                        for line in txt_file:
                            stringa += '<div style="font-size: 13px;">' + line + '</div>'
                        txt_file.close()
                    else:
                        self.dlg.textLog.append(self.tr('ATTENZIONE: il file TXT {} non è stato trovato, il Testo non verrà stampato.\n'.format(self.input_txt_path)))
                        QCoreApplication.processEvents()
                stringa += '<h3 style="text-align:center">Attesta e Certifica che</h3>'
                stringa += '<p> Il terreno oggetto della richiesta e distinto in Catasto al foglio <b>' + sel_foglio + '</b> con il mappale <b>' + sel_particella + '</b> interseca le seguenti mappe del <b>' + selectedGroup + '</b>:<br></p>'
                for key, value in print_dict.items():
                    if self.checkAreaBox == True:
                        stringa += '<p><b>' + value[0] + '</b><br>' + value[1] + '<br>' + value[2] + '<br>' + value[3] + '<br>' + value[4] + '<br>' + value[5] + '<br><br></p>'
                    else:
                        stringa += '<p><b>' + value[0] + '</b><br>' + value[1] + '<br>' + value[2] + '<br>' + value[3] + '<br>' + value[4] + '<br><br></p>'
                #####capire perchè non funziona il tag style dentro l'img..se provo a creare un file htm con quel tag e lo visualizzo su web funziona vedi file test.html in immagini
                stringa += '<p style="text-align:center"><img src="' + img_path_file + '"></p>'
                stringa += '<p style="text-align:center"> Il presente CDU è stato creato automaticamente in data {} alle ore {} utilizzando il plugin CDU Creator di QGIS.</p><br>'.format(datetime.now().strftime("%d-%m-%Y"), datetime.now().strftime("%H:%M:%S"))
                stringa += '<p>Si rilascia la presente per gli usi consentiti dalla legge.</p><br><p style="text-align:right"> Il Responsabile del Servizio</p>'
                stringa += '</body></html>'
                doc = QTextDocument()
                doc.setHtml(stringa)
                doc.print(printer)
            else:
                self.dlg.textLog.append(self.tr('ATTENZIONE: il terreno identificato dal foglio {} e mappale {} non interseca alcun layer. Il CDU non verrà creato.\n'.format(sel_foglio, sel_particella)))
                QCoreApplication.processEvents()
            
            self.lyr.selectByExpression("FOGLIO={} AND MAPPALE={}".format(sel_foglio, sel_particella))
            
            #rimuove il gruppo temporaneo
            rm_group = self.root.findGroup('temp')
            if rm_group is not None:
                for child in rm_group.children():
                    QgsProject.instance().removeMapLayer(child.layerId())
                self.root.removeChildNode(rm_group)
            map.refresh()
            
            self.dlg.textLog.append(self.tr('Il file PDF {} è stato salvato nella cartella {}.\n'.format(cdu_pdf_name, self.cdu_path_folder)))
            QCoreApplication.processEvents()
            self.dlg.textLog.append(self.tr('PROCESSO TERMINATO...\n'))
            QCoreApplication.processEvents()