/**
 * 基于bootstrap样式的上传插件
 * 调用方式如下
$(function(){
	$('#test01').bootstrapFileInput({
		width: '380px',				// 整个控件的宽度
		btnWidth: '80px',			// 按钮的宽度
		fileInputId: 'fileupload01',// 赋予内置的 (input type="file")一个id，以供外部使用
		fileInputName: 'deployItem'	// 赋予内置的 (input type="file")一个name，供表单提交使用
	});
});
 * 
 * @author: zyang
 */
(function($){
	$.fn.extend({
		bootstrapFileInput: function(options){
			var opts = $.extend({}, $.fn.bootstrapFileInput.defaults, options);
			var $this = this;
			$this.css({
				width: opts.width,
				position: 'relative',
				display: 'inline-block'
			});
			var pathTxtWidth = parseInt(opts.width) - parseInt(opts.btnWidth) - 30 + 'px';
			var $pathTxt = $('<input type="text" />');
			var $browseBtn = $('<button type="button">浏&nbsp;&nbsp;览</button>');
			var $fileInput = $('<input type="file"/>');
			$pathTxt.css({
					width: pathTxtWidth
			}).attr({
					disabled: 'disabled'
				});
			$browseBtn.addClass('btn btn-primary').css({
				'width': opts.btnWidth,
				'margin-bottom': '10px'
			});
			$fileInput.css({
				'width': opts.btnWidth,
				'position': 'absolute',
				'opacity': 0
			});
			if(opts.fileInputId){
				$fileInput.attr({
					id: opts.fileInputId,
					name: opts.fileInputName
				});
			}
			// safari内核浏览器无法触发file类型的input的click事件，所以只能用透明度为0的方式叠在按钮上
			if($.browser.safari){
				var $pathWrap = $('<div>').css({
					display: 'inline-block', 
					width: pathTxtWidth
				});
				var $btnWrap = $('<div>').css({
					display: 'inline-block',
					width: parseInt(opts.btnWidth) + 5 + 'px',
					position: 'relative',
					overflow: 'hidden',
					'margin-left': '23px'
				});
				$fileInput.css({
					right: '5px'
				});
				$pathWrap.append($pathTxt);
				$btnWrap.append($browseBtn).append($fileInput);
				$this.append($pathWrap).append($btnWrap);
			} else {
				$browseBtn.css({
					'margin-left': '10px'
				});
				$fileInput.css({
					left: '0px',
					'z-index': -1
				});
				$this.append($pathTxt).append($browseBtn).append($fileInput);
				$browseBtn.click(function(){
					$fileInput.click();
				});
			}
			
			$fileInput.change(function(){
				$this.attr('data-path', this.value);
				$pathTxt.val(this.value);
			});
		}
	});
	$.fn.bootstrapFileInput.defaults = {
		width: '400px',
		btnWidth: '80px',
		fileInputId: '',
		fileInputName: ''
	}
})(jQuery);