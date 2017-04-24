//Maya ASCII 2016 scene
//Name: axis.ma
//Last modified: Mon, Aug 22, 2016 04:02:17 PM
//Codeset: 1252
requires maya "2016";
requires -nodeType "ikSpringSolver" "ikSpringSolver" "1.0";
requires "stereoCamera" "10.0";
currentUnit -l centimeter -a degree -t ntsc;
fileInfo "application" "maya";
fileInfo "product" "Maya 2016";
fileInfo "version" "2016";
fileInfo "cutIdentifier" "201511301000-979500";
fileInfo "osv" "Microsoft Windows 8 Enterprise Edition, 64-bit  (Build 9200)\n";
createNode transform -s -n "persp";
	rename -uid "887B029F-4186-7709-7915-CEB8081836DB";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 0.93243199195714666 1.9534415062566668 -1.059453862149347 ;
	setAttr ".r" -type "double3" -54.938352729688596 500.59999999994426 0 ;
createNode camera -s -n "perspShape" -p "persp";
	rename -uid "3D874470-4F95-BE94-09BD-0C859FEA485E";
	setAttr -k off ".v" no;
	setAttr ".fl" 34.999999999999993;
	setAttr ".coi" 2.3156465090449188;
	setAttr ".imn" -type "string" "persp";
	setAttr ".den" -type "string" "persp_depth";
	setAttr ".man" -type "string" "persp_mask";
	setAttr ".tp" -type "double3" 0 0.25 0 ;
	setAttr ".hc" -type "string" "viewSet -p %camera";
createNode transform -s -n "top";
	rename -uid "E89C2D6E-4183-142C-94B3-2BA78656076C";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 0 100.1 0 ;
	setAttr ".r" -type "double3" -89.999999999999986 0 0 ;
createNode camera -s -n "topShape" -p "top";
	rename -uid "7C87F98F-46DA-97E8-9224-85A644AF8655";
	setAttr -k off ".v" no;
	setAttr ".rnd" no;
	setAttr ".coi" 100.1;
	setAttr ".ow" 30;
	setAttr ".imn" -type "string" "top";
	setAttr ".den" -type "string" "top_depth";
	setAttr ".man" -type "string" "top_mask";
	setAttr ".hc" -type "string" "viewSet -t %camera";
	setAttr ".o" yes;
createNode transform -s -n "front";
	rename -uid "5242177E-446E-51C5-8A3A-A0BD4F639F82";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 0 0 100.1 ;
createNode camera -s -n "frontShape" -p "front";
	rename -uid "68B87EF5-49CD-7E4B-5AE8-10A5122EF165";
	setAttr -k off ".v" no;
	setAttr ".rnd" no;
	setAttr ".coi" 100.1;
	setAttr ".ow" 30;
	setAttr ".imn" -type "string" "front";
	setAttr ".den" -type "string" "front_depth";
	setAttr ".man" -type "string" "front_mask";
	setAttr ".hc" -type "string" "viewSet -f %camera";
	setAttr ".o" yes;
createNode transform -s -n "side";
	rename -uid "8F039327-4586-8179-F90B-77B66C541703";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 100.1 0 0 ;
	setAttr ".r" -type "double3" 0 89.999999999999986 0 ;
createNode camera -s -n "sideShape" -p "side";
	rename -uid "1244017F-4F8C-99B6-1D7F-ADAA6C4FF538";
	setAttr -k off ".v" no;
	setAttr ".rnd" no;
	setAttr ".coi" 100.1;
	setAttr ".ow" 30;
	setAttr ".imn" -type "string" "side";
	setAttr ".den" -type "string" "side_depth";
	setAttr ".man" -type "string" "side_mask";
	setAttr ".hc" -type "string" "viewSet -s %camera";
	setAttr ".o" yes;
createNode transform -n "axis";
	rename -uid "C7482023-4264-A9D4-E970-2EA24203DAA4";
createNode mesh -n "axisShape" -p "axis";
	rename -uid "494C0715-4BFD-AB94-885B-599E1E360D53";
	setAttr -k off ".v";
	setAttr ".iog[0].og[0].gcl" -type "componentList" 1 "f[0:17]";
	setAttr ".vir" yes;
	setAttr ".vif" yes;
	setAttr ".uvst[0].uvsn" -type "string" "map1";
	setAttr -s 54 ".uvst[0].uvsp[0:53]" -type "float2" 0.5 0 0.34375 0.15624999
		 0.5 0.3125 0.65625 0.15625 0.375 0.3125 0.4375 0.3125 0.5 0.3125 0.5625 0.3125 0.625
		 0.3125 0.375 0.68843985 0.4375 0.68843985 0.5 0.68843985 0.5625 0.68843985 0.625
		 0.68843985 0.5 0.6875 0.34375 0.84375 0.5 1 0.65625 0.84375 0.375 0.3125 0.4375 0.3125
		 0.4375 0.68843985 0.375 0.68843985 0.5 0.3125 0.5 0.68843985 0.5625 0.3125 0.5625
		 0.68843985 0.625 0.3125 0.625 0.68843985 0.5 0 0.65625 0.15625 0.5 0.3125 0.34375
		 0.15624999 0.5 1 0.34375 0.84375 0.5 0.6875 0.65625 0.84375 0.375 0.3125 0.4375 0.3125
		 0.4375 0.68843985 0.375 0.68843985 0.5 0.3125 0.5 0.68843985 0.5625 0.3125 0.5625
		 0.68843985 0.625 0.3125 0.625 0.68843985 0.5 0 0.65625 0.15625 0.5 0.3125 0.34375
		 0.15624999 0.5 1 0.34375 0.84375 0.5 0.6875 0.65625 0.84375;
	setAttr ".cuvs" -type "string" "map1";
	setAttr ".dcol" yes;
	setAttr ".dcc" -type "string" "Ambient+Diffuse";
	setAttr ".clst[0].clsn" -type "string" "colorSet1";
	setAttr -s 72 ".clst[0].clsp[0:71]"  1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1
		 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1
		 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 0 0
		 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1
		 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1 0 0 1 1
		 0 0 1 1 0 0 1 1 0 0 1 1 1 1 0 1 1 1 0 1 1 1 0 1 1 1 0 1 1 1 0 1 1 1 0 1 1 1 0 1 1
		 1 0 1 1 1 0 1 1 1 0 1 1 1 0 1 1 1 0 1 1 1 0 1 1 1 0 1 1 1 0 1 1 1 0 1 1 1 0 1 1 1
		 0 1 1 1 0 1 1 1 0 1 1 1 0 1 1 1 0 1 1 1 0 1 1 1 0 1;
	setAttr ".covm[0]"  0 1 1;
	setAttr ".cdvm[0]"  0 1 1;
	setAttr -s 24 ".vt[0:23]"  0 0.02 -2.6226832e-009 0 1.7484555e-009 0.02
		 0 -0.02 8.7422775e-010 0 1.1102484e-018 -0.02 0.5 0.02 -2.6226832e-009 0.5 1.7484568e-009 0.02
		 0.5 -0.02 8.7422775e-010 0.5 1.3333779e-015 -0.02 2.6226832e-009 0.02 0 -0.02 1.7484554e-009 0
		 -8.7422775e-010 -0.02 0 0.02 0 0 2.6226832e-009 0.02 0.5 -0.02 1.7484556e-009 0.5
		 -8.7422775e-010 -0.02 0.5 0.02 1.110223e-016 0.5 2.6226832e-009 0 -0.02 -0.02 0 -1.7484555e-009
		 -8.7422775e-010 0 0.02 0.02 0 0 2.6226832e-009 0.5 -0.02 -0.02 0.5 -1.7484555e-009
		 -8.7422775e-010 0.5 0.02 0.02 0.5 0;
	setAttr -s 36 ".ed[0:35]"  0 1 0 1 2 0 2 3 0 3 0 0 4 5 0 5 6 0 6 7 0
		 7 4 0 0 4 0 1 5 0 2 6 0 3 7 0 8 9 0 9 10 0 10 11 0 11 8 0 12 13 0 13 14 0 14 15 0
		 15 12 0 8 12 0 9 13 0 10 14 0 11 15 0 16 17 0 17 18 0 18 19 0 19 16 0 20 21 0 21 22 0
		 22 23 0 23 20 0 16 20 0 17 21 0 18 22 0 19 23 0;
	setAttr -s 18 -ch 72 ".fc[0:17]" -type "polyFaces" 
		f 4 0 9 -5 -9
		mu 0 4 4 5 10 9
		mc 0 4 0 5 6 11
		f 4 1 10 -6 -10
		mu 0 4 5 6 11 10
		mc 0 4 3 14 15 8
		f 4 2 11 -7 -11
		mu 0 4 6 7 12 11
		mc 0 4 12 20 21 17
		f 4 3 8 -8 -12
		mu 0 4 7 8 13 12
		mc 0 4 18 2 9 23
		f 4 -4 -3 -2 -1
		mu 0 4 0 3 2 1
		mc 0 4 1 19 13 4
		f 4 4 5 6 7
		mu 0 4 16 15 14 17
		mc 0 4 10 7 16 22
		f 4 12 21 -17 -21
		mu 0 4 18 19 20 21
		mc 0 4 24 29 30 35
		f 4 13 22 -18 -22
		mu 0 4 19 22 23 20
		mc 0 4 27 38 39 32
		f 4 14 23 -19 -23
		mu 0 4 22 24 25 23
		mc 0 4 36 44 45 41
		f 4 15 20 -20 -24
		mu 0 4 24 26 27 25
		mc 0 4 42 26 33 47
		f 4 -16 -15 -14 -13
		mu 0 4 28 29 30 31
		mc 0 4 25 43 37 28
		f 4 16 17 18 19
		mu 0 4 32 33 34 35
		mc 0 4 34 31 40 46
		f 4 24 33 -29 -33
		mu 0 4 36 37 38 39
		mc 0 4 48 51 63 60
		f 4 25 34 -30 -34
		mu 0 4 37 40 41 38
		mc 0 4 52 54 66 64
		f 4 26 35 -31 -35
		mu 0 4 40 42 43 41
		mc 0 4 55 57 69 67
		f 4 27 32 -32 -36
		mu 0 4 42 44 45 43
		mc 0 4 58 49 61 70
		f 4 -28 -27 -26 -25
		mu 0 4 46 47 48 49
		mc 0 4 50 59 56 53
		f 4 28 29 30 31
		mu 0 4 50 51 52 53
		mc 0 4 62 65 68 71;
	setAttr ".cd" -type "dataPolyComponent" Index_Data Edge 0 ;
	setAttr ".cvd" -type "dataPolyComponent" Index_Data Vertex 0 ;
	setAttr ".pd[0]" -type "dataPolyComponent" Index_Data UV 0 ;
	setAttr ".hfd" -type "dataPolyComponent" Index_Data Face 0 ;
createNode lightLinker -s -n "lightLinker1";
	rename -uid "282069FF-4B36-4061-E8A5-81BC411015E4";
	setAttr -s 2 ".lnk";
	setAttr -s 2 ".slnk";
createNode displayLayerManager -n "layerManager";
	rename -uid "8358D5B4-43DD-A3E0-2678-F0B5085B1815";
createNode displayLayer -n "defaultLayer";
	rename -uid "937706BD-4DB4-31A6-C4C6-958E7133D88B";
createNode renderLayerManager -n "renderLayerManager";
	rename -uid "626821DB-4B08-023E-561E-759AC60006A8";
createNode renderLayer -n "defaultRenderLayer";
	rename -uid "AE4E9F85-4690-8D51-139E-08AA00D5FB16";
	setAttr ".g" yes;
createNode groupId -n "groupId1";
	rename -uid "91801EB0-419C-5E34-E35B-3393B14A8220";
	setAttr ".ihi" 0;
createNode script -n "sceneConfigurationScriptNode";
	rename -uid "B2C9D197-4A6A-E5CC-DB3A-04AA39F125B0";
	setAttr ".b" -type "string" "playbackOptions -min 1 -max 120 -ast 1 -aet 200 ";
	setAttr ".st" 6;
select -ne :time1;
	setAttr -av -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -k on ".o" 1;
	setAttr ".unw" 1;
select -ne :hardwareRenderingGlobals;
	setAttr ".otfna" -type "stringArray" 22 "NURBS Curves" "NURBS Surfaces" "Polygons" "Subdiv Surface" "Particles" "Particle Instance" "Fluids" "Strokes" "Image Planes" "UI" "Lights" "Cameras" "Locators" "Joints" "IK Handles" "Deformers" "Motion Trails" "Components" "Hair Systems" "Follicles" "Misc. UI" "Ornaments"  ;
	setAttr ".otfva" -type "Int32Array" 22 0 1 1 1 1 1
		 1 1 1 0 0 0 0 0 0 0 0 0
		 0 0 0 0 ;
	setAttr ".fprt" yes;
select -ne :renderPartition;
	setAttr -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -s 2 ".st";
	setAttr -cb on ".an";
	setAttr -cb on ".pt";
select -ne :renderGlobalsList1;
	setAttr -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -k on ".nds";
	setAttr -cb on ".bnm";
select -ne :defaultShaderList1;
	setAttr -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -s 4 ".s";
select -ne :postProcessList1;
	setAttr -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -s 2 ".p";
select -ne :defaultRenderingList1;
select -ne :initialShadingGroup;
	setAttr -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -av -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -k on ".mwc";
	setAttr -cb on ".an";
	setAttr -cb on ".il";
	setAttr -cb on ".vo";
	setAttr -cb on ".eo";
	setAttr -cb on ".fo";
	setAttr -cb on ".epo";
	setAttr -k on ".ro" yes;
select -ne :initialParticleSE;
	setAttr -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -av -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr -k on ".mwc";
	setAttr -cb on ".an";
	setAttr -cb on ".il";
	setAttr -cb on ".vo";
	setAttr -cb on ".eo";
	setAttr -cb on ".fo";
	setAttr -cb on ".epo";
	setAttr -k on ".ro" yes;
select -ne :defaultRenderGlobals;
	setAttr -k on ".cch";
	setAttr -k on ".nds";
	setAttr -k on ".clip";
	setAttr -k on ".edm";
	setAttr -k on ".edl";
	setAttr -av -k on ".esr";
	setAttr -k on ".ors";
	setAttr -k on ".gama";
	setAttr ".fs" 1;
	setAttr ".ef" 10;
	setAttr -k on ".bfs";
	setAttr -k on ".be";
	setAttr -k on ".fec";
	setAttr -k on ".ofc";
	setAttr -k on ".comp";
	setAttr -k on ".cth";
	setAttr -k on ".soll";
	setAttr -k on ".rd";
	setAttr -k on ".lp";
	setAttr -k on ".sp";
	setAttr -k on ".shs";
	setAttr -k on ".lpr";
	setAttr -k on ".mm";
	setAttr -k on ".npu";
	setAttr -k on ".itf";
	setAttr -k on ".shp";
	setAttr -k on ".uf";
	setAttr -k on ".oi";
	setAttr -k on ".rut";
	setAttr -av -k on ".mbf";
	setAttr -k on ".afp";
	setAttr -k on ".pfb";
	setAttr -av -k on ".bll";
	setAttr -k on ".bls";
	setAttr -k on ".smv";
	setAttr -k on ".ubc";
	setAttr -k on ".mbc";
	setAttr -k on ".udbx";
	setAttr -k on ".smc";
	setAttr -k on ".kmv";
	setAttr -k on ".rlen";
	setAttr -av -k on ".frts";
	setAttr -k on ".tlwd";
	setAttr -k on ".tlht";
	setAttr -k on ".jfc";
select -ne :defaultResolution;
	setAttr ".pa" 1;
select -ne :hardwareRenderGlobals;
	setAttr -k on ".cch";
	setAttr -cb on ".ihi";
	setAttr -k on ".nds";
	setAttr -cb on ".bnm";
	setAttr ".ctrs" 256;
	setAttr ".btrs" 512;
	setAttr -k off ".fbfm";
	setAttr -k off -cb on ".ehql";
	setAttr -k off -cb on ".eams";
	setAttr -k off -cb on ".eeaa";
	setAttr -k off -cb on ".engm";
	setAttr -k off -cb on ".mes";
	setAttr -k off -cb on ".emb";
	setAttr -av -k off -cb on ".mbbf";
	setAttr -k off -cb on ".mbs";
	setAttr -k off -cb on ".trm";
	setAttr -k off -cb on ".tshc";
	setAttr -k off ".enpt";
	setAttr -k off -cb on ".clmt";
	setAttr -k off -cb on ".tcov";
	setAttr -k off -cb on ".lith";
	setAttr -k off -cb on ".sobc";
	setAttr -k off -cb on ".cuth";
	setAttr -k off -cb on ".hgcd";
	setAttr -k off -cb on ".hgci";
	setAttr -k off -cb on ".mgcs";
	setAttr -k off -cb on ".twa";
	setAttr -k off -cb on ".twz";
	setAttr -k on ".hwcc";
	setAttr -k on ".hwdp";
	setAttr -k on ".hwql";
	setAttr -k on ".hwfr";
select -ne :ikSystem;
	setAttr -s 4 ".sol";
connectAttr "groupId1.id" "axisShape.iog.og[0].gid";
connectAttr ":initialShadingGroup.mwc" "axisShape.iog.og[0].gco";
relationship "link" ":lightLinker1" ":initialShadingGroup.message" ":defaultLightSet.message";
relationship "link" ":lightLinker1" ":initialParticleSE.message" ":defaultLightSet.message";
relationship "shadowLink" ":lightLinker1" ":initialShadingGroup.message" ":defaultLightSet.message";
relationship "shadowLink" ":lightLinker1" ":initialParticleSE.message" ":defaultLightSet.message";
connectAttr "layerManager.dli[0]" "defaultLayer.id";
connectAttr "renderLayerManager.rlmi[0]" "defaultRenderLayer.rlid";
connectAttr "defaultRenderLayer.msg" ":defaultRenderingList1.r" -na;
connectAttr "axisShape.iog.og[0]" ":initialShadingGroup.dsm" -na;
connectAttr "groupId1.msg" ":initialShadingGroup.gn" -na;
// End of axis.ma
