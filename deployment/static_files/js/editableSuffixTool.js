var editableSuffixMap = {
	xml: 'xml',
	html: 'htmlmixed',
	jsp: 'htmlmixed',
	js: 'javascript',
	css: 'css',
	properties: 'properties',
	mysql: 'mysql'
}

function isFileEditable(filename){
	var suffix = getFilenameSuffix(filename);
	return suffix in editableSuffixMap;
}

function findEditModeByFilename(filename){
	var suffix = getFilenameSuffix(filename);
	if(!suffix){
		return '';
	}
	return editableSuffixMap[suffix] || '';
}
function getFilenameSuffix(filename){
	if(!filename){
		return '';
	}
	var re = /\.(\w+)$/i;
	var matchResult = re.exec(filename);
	if (!matchResult || matchResult.length < 2){
		return '';
	}
	return matchResult[1];
}
