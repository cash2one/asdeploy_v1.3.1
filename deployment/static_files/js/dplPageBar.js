function PageBar(options){
	for(var key in options){
		this[key] = options[key];
	}
	if(typeof this['pageBar'] == 'string'){
		this['pageBar'] = document.getElementById(this['pageBar']);
	}
	if(!this['totalPage'] || !this['pageBar']){
		return null;
	}
	this.init();
}
PageBar.prototype = {
	curPage: 1,
	numPerPage: 20,
	maxBtnNum: 15,
	curPageSiblingBtnNum: 3,
	init: function(){
		this.initBtns();
		this.initPanel();
	},
	initBtns: function(){
		if(this.totalPage < 1){
			return;
		}
		var _this = this;
		var btnGrpDiv = document.createElement('div');
		btnGrpDiv.className = 'btn_grp';
		nums = [];
		for(var i=1; i<=this.totalPage; i++){
			nums.push(i);
		}
		if(this.maxBtnNum < this.totalPage){
			for(var i=this.curPageSiblingBtnNum, count = nums.length; 
					count > this.maxBtnNum && i<this.totalPage - this.curPageSiblingBtnNum; i++){
				var l = this.curPage - i;
				if(l > 2){
					nums[l-1] = 0;
					count--;
				}
				if(count <= this.maxBtnNum){
					break;
				}
				var r = this.curPage + i;
				if(r < this.totalPage - 2){
					nums[r-1] = 0;
					count--;
				}
				if(count <= this.maxBtnNum){
					break;
				}
			}
		}
		var btnNums = [],
			btnArr = [];
		for(var i=0, l=nums.length; i<l; i++){
			nums[i] > 0 && (btnNums.push(nums[i]));
		}
		for(var i=0, l=btnNums.length; i<l; i++){
			var btn = document.createElement('div');
			btn.innerHTML = btnNums[i];
			btn.className = 'btn';
			if(btnNums[i] == this.curPage){
				btn.className += ' cur_sel';
			}
			btn.getIndex = (function(index){
				return function(){
					return index;
				}
			})(btnNums[i]);
			btn.onclick = function(){
				_this.clickBtn(this.getIndex());
			};
			btnArr.push(btn);
		}
		for(var i=0, l=btnArr.length; i<l; i++){
			btnGrpDiv.appendChild(btnArr[i]);
			if(btnArr[i+1] && btnArr[i+1].getIndex() - btnArr[i].getIndex() > 1){
				var omitDiv = document.createElement('div');
				omitDiv.innerHTML = '...';
				btnGrpDiv.appendChild(omitDiv);
			}
		}
		this['pageBar'].appendChild(btnGrpDiv);
	},
	initPanel: function(){
		var _this = this;
		var panelDiv = document.createElement('div'),
			wrapDiv = document.createElement('div'),
			innerDiv = document.createElement('div'),
			leftBtn = document.createElement('a'),
			rightBtn = document.createElement('a'),
			span = document.createElement('span'),
			footpadDiv = document.createElement('div');
		panelDiv.className = 'cur_page_panel';
		wrapDiv.style.display = 'inline-block';
		leftBtn.innerHTML = '&lt;&lt;';
		leftBtn.href = 'javascript:void(0);';
		rightBtn.innerHTML = '&gt;&gt;';
		rightBtn.href = 'javascript:void(0);';
		leftBtn.onclick = function(){
			var idx = Math.max(1, _this.curPage - 1);
			_this.clickBtn(idx);
		};
		rightBtn.onclick = function(){
			var idx = Math.min(_this.totalPage, _this.curPage + 1);
			_this.clickBtn(idx);
		}
		var str = '当前第[' + this.curPage + ']页,共[' + this.totalPage + ']页';
		span.innerHTML = str;
		with(footpadDiv.style){
			height = '5px';
			// lineHeight = '1px';
		}
		footpadDiv.innerHTML = '&nbsp;'
		
		innerDiv.appendChild(leftBtn);
		innerDiv.appendChild(span);
		innerDiv.appendChild(rightBtn);
		
		wrapDiv.appendChild(innerDiv);
		wrapDiv.appendChild(footpadDiv);
		
		panelDiv.appendChild(wrapDiv);
		this.pageBar.appendChild(panelDiv);
	},
	clickBtn: function(index){
		alert(index);
		return false;
	},
}